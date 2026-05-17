"""Tests for the journal_read tool handler."""

from __future__ import annotations

import json

from bodhisattva_mcp.journal import Journal, PauseRecord
from bodhisattva_mcp.tools.journal_read import JournalReadInput, handle_journal_read


def test_returns_record_with_parsed_wisdom_frame(journal: Journal) -> None:
    frame = {
        "emotional_context": "routine",
        "sensitivity_level": "low",
        "is_consequential": False,
        "consequential_reason": None,
        "wellbeing_risk": False,
        "affected_parties": ["user"],
        "recommended_posture": "steady",
        "guidance": "ordinary send",
        "reflection_invitation": None,
    }
    rec_id = journal.create(
        PauseRecord(
            draft="d",
            subject="Hello",
            recipient="r@x.com",
            recipient_context="acquaintance",
            wisdom_frame_json=json.dumps(frame),
            decision="proceed",
        )
    )

    result = handle_journal_read(JournalReadInput(id=rec_id), journal=journal)

    assert result["found"] is True
    record = result["record"]
    assert record["id"] == rec_id
    assert record["decision"] == "proceed"
    assert record["subject"] == "Hello"
    assert record["recipient"] == "r@x.com"
    assert record["recipient_context"] == "acquaintance"
    assert record["wisdom_frame"] == frame
    assert "wisdom_frame_parse_error" not in record


def test_missing_id_returns_not_found(journal: Journal) -> None:
    result = handle_journal_read(JournalReadInput(id=99999), journal=journal)
    assert result == {"found": False, "id": 99999}


def test_malformed_wisdom_frame_json_is_reported(journal: Journal) -> None:
    rec_id = journal.create(
        PauseRecord(
            draft="d",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json="not valid json {",
            decision="proceed",
        )
    )

    result = handle_journal_read(JournalReadInput(id=rec_id), journal=journal)

    assert result["found"] is True
    assert result["record"]["wisdom_frame"] is None
    assert result["record"]["wisdom_frame_parse_error"] is True


def test_non_object_wisdom_frame_json_is_reported(journal: Journal) -> None:
    rec_id = journal.create(
        PauseRecord(
            draft="d",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json='"just a string"',
            decision="proceed",
        )
    )

    result = handle_journal_read(JournalReadInput(id=rec_id), journal=journal)

    assert result["found"] is True
    assert result["record"]["wisdom_frame"] is None
    assert result["record"]["wisdom_frame_parse_error"] is True
