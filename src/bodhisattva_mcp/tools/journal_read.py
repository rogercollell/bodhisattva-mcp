"""MCP tool: fetch one journal entry by id with parsed wisdom frame."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from bodhisattva_mcp.journal import Journal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JournalReadInput:
    id: int


def handle_journal_read(inp: JournalReadInput, *, journal: Journal) -> dict[str, Any]:
    record = journal.get(inp.id)
    if record is None:
        return {"found": False, "id": inp.id}

    wisdom_frame: dict[str, Any] | None
    parse_error = False
    try:
        wisdom_frame = json.loads(record.wisdom_frame_json)
    except json.JSONDecodeError:
        logger.warning("Malformed wisdom_frame_json in journal entry %s", record.id)
        wisdom_frame = None
        parse_error = True

    payload_record: dict[str, Any] = {
        "id": record.id,
        "timestamp": record.timestamp,
        "draft": record.draft,
        "subject": record.subject,
        "recipient": record.recipient,
        "recipient_context": record.recipient_context,
        "decision": record.decision,
        "wisdom_frame": wisdom_frame,
        "user_choice": record.user_choice,
        "final_sent_text": record.final_sent_text,
        "message_id": record.message_id,
    }
    if parse_error:
        payload_record["wisdom_frame_parse_error"] = True

    return {"found": True, "record": payload_record}
