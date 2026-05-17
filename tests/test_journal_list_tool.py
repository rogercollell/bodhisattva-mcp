"""Tests for the journal_list tool handler."""

from __future__ import annotations

import json

from bodhisattva_mcp.journal import Journal, PauseRecord
from bodhisattva_mcp.tools.journal_list import JournalListInput, handle_journal_list


def _make_frame(sensitivity: str = "low", guidance: str = "fine") -> str:
    return json.dumps(
        {
            "emotional_context": "routine",
            "sensitivity_level": sensitivity,
            "is_consequential": False,
            "consequential_reason": None,
            "wellbeing_risk": False,
            "affected_parties": ["user"],
            "recommended_posture": "steady",
            "guidance": guidance,
            "reflection_invitation": None,
        }
    )


def test_returns_slim_rows_with_snippet_and_sensitivity(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="d",
            subject="Hello",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(sensitivity="high", guidance="A" * 300),
            decision="revise",
        )
    )

    result = handle_journal_list(JournalListInput(), journal=journal)

    assert "records" in result
    assert len(result["records"]) == 1
    row = result["records"][0]
    assert row["recipient"] == "r@x.com"
    assert row["subject"] == "Hello"
    assert row["decision"] == "revise"
    assert row["sensitivity_level"] == "high"
    assert row["guidance_snippet"] == "A" * 200
    assert len(row["guidance_snippet"]) == 200
    # Slim row must NOT contain draft or full wisdom_frame.
    assert "draft" not in row
    assert "wisdom_frame" not in row


def test_filter_by_recipient(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="a",
            subject="s",
            recipient="alice@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="b",
            subject="s",
            recipient="bob@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="proceed",
        )
    )

    result = handle_journal_list(JournalListInput(recipient="alice@x.com"), journal=journal)
    assert len(result["records"]) == 1
    assert result["records"][0]["recipient"] == "alice@x.com"


def test_filter_by_decision(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="a",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="b",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="hold",
        )
    )

    result = handle_journal_list(JournalListInput(decision="hold"), journal=journal)
    assert len(result["records"]) == 1
    assert result["records"][0]["decision"] == "hold"


def test_filter_by_since(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="old",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="proceed",
            timestamp="2026-01-01T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="new",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(),
            decision="proceed",
            timestamp="2026-06-01T00:00:00+00:00",
        )
    )

    result = handle_journal_list(
        JournalListInput(since="2026-03-01T00:00:00+00:00"), journal=journal
    )
    assert len(result["records"]) == 1
    assert result["records"][0]["timestamp"].startswith("2026-06")


def test_invalid_decision_returns_error(journal: Journal) -> None:
    result = handle_journal_list(JournalListInput(decision="bogus"), journal=journal)
    assert result["code"] == "invalid_argument"
    assert "decision" in result["error"]
    assert "records" not in result


def test_invalid_since_returns_error(journal: Journal) -> None:
    result = handle_journal_list(JournalListInput(since="not-a-date"), journal=journal)
    assert result["code"] == "invalid_argument"
    assert "since" in result["error"]
    assert "records" not in result


def test_limit_clamps_low(journal: Journal) -> None:
    for i in range(3):
        journal.create(
            PauseRecord(
                draft=f"d{i}",
                subject="s",
                recipient="r@x.com",
                recipient_context=None,
                wisdom_frame_json=_make_frame(),
                decision="proceed",
            )
        )

    # limit=0 clamps to 1
    result = handle_journal_list(JournalListInput(limit=0), journal=journal)
    assert len(result["records"]) == 1

    # negative clamps to 1
    result = handle_journal_list(JournalListInput(limit=-5), journal=journal)
    assert len(result["records"]) == 1


def test_limit_clamps_high(journal: Journal) -> None:
    for i in range(5):
        journal.create(
            PauseRecord(
                draft=f"d{i}",
                subject="s",
                recipient="r@x.com",
                recipient_context=None,
                wisdom_frame_json=_make_frame(),
                decision="proceed",
            )
        )

    # limit=9999 is accepted but only 5 rows exist
    result = handle_journal_list(JournalListInput(limit=9999), journal=journal)
    assert len(result["records"]) == 5


def test_one_malformed_row_does_not_poison_list(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="good",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(sensitivity="medium", guidance="all fine"),
            decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="bad",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json="not valid json",
            decision="hold",
        )
    )

    result = handle_journal_list(JournalListInput(), journal=journal)
    assert len(result["records"]) == 2

    bad_row = next(r for r in result["records"] if r["decision"] == "hold")
    assert bad_row["sensitivity_level"] is None
    assert bad_row["guidance_snippet"] == ""

    good_row = next(r for r in result["records"] if r["decision"] == "proceed")
    assert good_row["sensitivity_level"] == "medium"
    assert good_row["guidance_snippet"] == "all fine"


def test_non_dict_wisdom_frame_falls_back_gracefully(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="d",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json='"just a string"',
            decision="proceed",
        )
    )

    result = handle_journal_list(JournalListInput(), journal=journal)

    assert len(result["records"]) == 1
    row = result["records"][0]
    assert row["sensitivity_level"] is None
    assert row["guidance_snippet"] == ""
