"""Tests for the local SQLite journal."""

import json
from pathlib import Path

import pytest

from bodhisattva_mcp.journal import Journal, PauseRecord


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "journal.sqlite")


def test_create_and_get(journal: Journal) -> None:
    rec = PauseRecord(
        draft="Hi Alice",
        subject="Hello",
        recipient="alice@example.com",
        recipient_context="manager",
        wisdom_frame_json=json.dumps({"sensitivity_level": "medium"}),
        decision="proceed",
    )
    rec_id = journal.create(rec)
    assert isinstance(rec_id, int)
    assert rec_id > 0

    fetched = journal.get(rec_id)
    assert fetched is not None
    assert fetched.draft == "Hi Alice"
    assert fetched.subject == "Hello"
    assert fetched.recipient == "alice@example.com"
    assert fetched.decision == "proceed"
    assert fetched.id == rec_id


def test_get_missing_returns_none(journal: Journal) -> None:
    assert journal.get(999999) is None


def test_list_returns_newest_first(journal: Journal) -> None:
    ids = []
    for i in range(3):
        rec = PauseRecord(
            draft=f"d{i}",
            subject="s",
            recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json="{}",
            decision="proceed",
        )
        ids.append(journal.create(rec))

    listed = journal.list(limit=10)
    assert [r.id for r in listed] == list(reversed(ids))


def test_update_user_choice(journal: Journal) -> None:
    rec = PauseRecord(
        draft="d",
        subject="s",
        recipient="r@x.com",
        recipient_context=None,
        wisdom_frame_json="{}",
        decision="revise",
    )
    rec_id = journal.create(rec)

    journal.update_user_choice(
        rec_id,
        user_choice="revised_and_sent",
        final_sent_text="Revised body",
        message_id="gmail-123",
    )

    fetched = journal.get(rec_id)
    assert fetched is not None
    assert fetched.user_choice == "revised_and_sent"
    assert fetched.final_sent_text == "Revised body"
    assert fetched.message_id == "gmail-123"


def test_schema_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "journal.sqlite"
    Journal(db_path)
    Journal(db_path)  # Re-opening must not error.


def test_list_by_recipient(journal: Journal) -> None:
    journal.create(PauseRecord(draft="a", subject="s", recipient="alice@x.com",
                               recipient_context=None, wisdom_frame_json="{}", decision="proceed"))
    journal.create(PauseRecord(draft="b", subject="s", recipient="bob@x.com",
                               recipient_context=None, wisdom_frame_json="{}", decision="proceed"))
    journal.create(PauseRecord(draft="c", subject="s", recipient="alice@x.com",
                               recipient_context=None, wisdom_frame_json="{}", decision="revise"))

    alice_records = journal.list(limit=10, recipient="alice@x.com")
    assert len(alice_records) == 2
    assert all(r.recipient == "alice@x.com" for r in alice_records)
