"""MCP tool: list past wisdom-pauses with optional filters."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bodhisattva_mcp.journal import Journal, PauseRecord

logger = logging.getLogger(__name__)

_VALID_DECISIONS = frozenset({"proceed", "revise", "hold"})
_DEFAULT_LIMIT = 50
_MIN_LIMIT = 1
_MAX_LIMIT = 200
_SNIPPET_LEN = 200


@dataclass(frozen=True)
class JournalListInput:
    recipient: str | None = None
    decision: str | None = None
    since: str | None = None
    limit: int = _DEFAULT_LIMIT


def handle_journal_list(inp: JournalListInput, *, journal: Journal) -> dict[str, Any]:
    if inp.decision is not None and inp.decision not in _VALID_DECISIONS:
        return {
            "error": "invalid decision: must be one of proceed | revise | hold",
            "code": "invalid_argument",
        }
    if inp.since is not None:
        try:
            datetime.fromisoformat(inp.since)
        except ValueError:
            return {
                "error": "invalid since: must be an ISO 8601 timestamp",
                "code": "invalid_argument",
            }

    limit = max(_MIN_LIMIT, min(_MAX_LIMIT, inp.limit))

    records = journal.list(
        limit=limit,
        recipient=inp.recipient,
        decision=inp.decision,
        since=inp.since,
    )
    return {"records": [_to_slim(r) for r in records]}


def _to_slim(record: PauseRecord) -> dict[str, Any]:
    sensitivity_level: str | None = None
    guidance_snippet = ""
    try:
        parsed = json.loads(record.wisdom_frame_json)
    except json.JSONDecodeError:
        logger.warning("Malformed wisdom_frame_json in journal entry %s", record.id)
    else:
        if isinstance(parsed, dict):
            raw_level = parsed.get("sensitivity_level")
            if isinstance(raw_level, str):
                sensitivity_level = raw_level
            raw_guidance = parsed.get("guidance", "")
            if isinstance(raw_guidance, str):
                guidance_snippet = raw_guidance[:_SNIPPET_LEN].rstrip()
        else:
            logger.warning("wisdom_frame_json in journal entry %s is not a JSON object", record.id)

    return {
        "id": record.id,
        "timestamp": record.timestamp,
        "recipient": record.recipient,
        "subject": record.subject,
        "decision": record.decision,
        "sensitivity_level": sensitivity_level,
        "guidance_snippet": guidance_snippet,
        "user_choice": record.user_choice,
    }
