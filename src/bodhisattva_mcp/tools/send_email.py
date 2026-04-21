"""The single MCP tool: orchestrates framing, gating, sending, journaling."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from bodhisattva_mcp.attune.email_prompt import build_email_prompt
from bodhisattva_mcp.attune.models import SensitivityLevel, WisdomFrame
from bodhisattva_mcp.attune.wisdom_frame import _fallback_frame, _validate_and_build
from bodhisattva_mcp.gate import Decision, decide
from bodhisattva_mcp.gmail_client import (
    EmailToSend,
    GmailAuthError,
    GmailClient,
    GmailSendError,
)
from bodhisattva_mcp.journal import Journal, PauseRecord

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendEmailInput:
    to: str
    subject: str
    body: str
    context: str | None


def _frame_email(
    inp: SendEmailInput, domain: str, model: BaseChatModel
) -> WisdomFrame:
    prompt = build_email_prompt(
        draft=inp.body,
        subject=inp.subject,
        recipient=inp.to,
        recipient_context=inp.context,
        domain=domain,
    )
    try:
        response = model.invoke([HumanMessage(content=prompt)])
    except Exception:
        logger.warning("Framing model call failed", exc_info=True)
        return _fallback_frame(inp.body)

    try:
        raw = json.loads(_extract_text(response.content))
        return _validate_and_build(raw)
    except Exception:
        logger.warning("Framing response was not valid JSON / frame", exc_info=True)
        return _fallback_frame(inp.body)


def _extract_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in content
        )
    return str(content)


def handle_send_email(
    inp: SendEmailInput,
    *,
    model: BaseChatModel,
    gmail: GmailClient,
    journal: Journal,
    domain: str,
) -> dict[str, Any]:
    """Run the full pause flow for a send_email request."""
    # Validate input eagerly so bad recipients don't write a journal row.
    email = EmailToSend(to=inp.to, subject=inp.subject, body=inp.body)

    frame = _frame_email(inp, domain, model)
    outcome = decide(frame, draft=inp.body, model=model)

    record = PauseRecord(
        draft=inp.body,
        subject=inp.subject,
        recipient=inp.to,
        recipient_context=inp.context,
        wisdom_frame_json=frame.model_dump_json(),
        decision=outcome.decision.value,
    )
    record_id = journal.create(record)

    result: dict[str, Any] = {
        "decision": outcome.decision.value,
        "wisdom_frame": frame.model_dump(),
        "suggested_revision": outcome.suggested_revision,
        "message_id": None,
        "journal_entry_id": record_id,
        "error": None,
    }

    if outcome.decision is Decision.proceed:
        try:
            message_id = gmail.send(email)
        except (GmailAuthError, GmailSendError) as exc:
            journal.update_user_choice(record_id, user_choice="send_failed")
            result["decision"] = "hold"
            result["error"] = str(exc)
            return result

        journal.update_user_choice(
            record_id, user_choice="sent", final_sent_text=inp.body, message_id=message_id
        )
        result["message_id"] = message_id
        return result

    if outcome.decision is Decision.hold:
        # Reason lives inside wisdom_frame.guidance already; surface it at top.
        if frame.sensitivity_level == SensitivityLevel.critical:
            result["error"] = "Hold: critical wellbeing signal."
        return result

    # Decision.revise — caller (agent) presents suggested_revision to user.
    return result
