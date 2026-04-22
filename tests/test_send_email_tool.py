"""Integration tests for the send_email tool handler."""

from __future__ import annotations

import json

import pytest

from bodhisattva_mcp.gmail_client import FakeGmailClient, GmailAuthError
from bodhisattva_mcp.journal import Journal
from bodhisattva_mcp.tools.send_email import SendEmailInput, handle_send_email


def test_benign_email_proceeds_and_sends(
    journal: Journal, fake_gmail: FakeGmailClient, benign_llm
) -> None:
    result = handle_send_email(
        SendEmailInput(
            to="alice@example.com",
            subject="Meeting next week",
            body="Hi Alice, confirming 2pm Tuesday works.",
            context=None,
        ),
        model=benign_llm,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )

    assert result["decision"] == "proceed"
    assert result["message_id"] is not None
    assert result["suggested_revision"] is None
    assert len(fake_gmail.sent) == 1

    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    assert rec.decision == "proceed"
    assert rec.user_choice == "sent"
    assert rec.message_id == result["message_id"]


def test_consequential_email_revises_and_does_not_send(
    journal: Journal, fake_gmail: FakeGmailClient, consequential_llm
) -> None:
    result = handle_send_email(
        SendEmailInput(
            to="alice@company.com",
            subject="Q3 deadline",
            body="Alice, this is unreasonable and I'm done.",
            context="My manager. She set a Q3 deadline I think is unrealistic.",
        ),
        model=consequential_llm,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )

    assert result["decision"] == "revise"
    assert result["message_id"] is None
    assert result["suggested_revision"] is not None
    assert "Q3 deadline" in result["suggested_revision"]
    assert len(fake_gmail.sent) == 0  # No send yet.

    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    assert rec.decision == "revise"
    assert rec.user_choice is None  # Awaiting user's next move.


def test_critical_email_holds_and_does_not_send(
    journal: Journal, fake_gmail: FakeGmailClient, critical_llm
) -> None:
    result = handle_send_email(
        SendEmailInput(
            to="anyone@example.com",
            subject="help",
            body="I can't go on anymore.",
            context=None,
        ),
        model=critical_llm,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )

    assert result["decision"] == "hold"
    assert result["message_id"] is None
    frame = result["wisdom_frame"]
    assert frame["sensitivity_level"] == "critical"
    assert "988" in frame["guidance"]  # Crisis text preserved.
    assert len(fake_gmail.sent) == 0


def test_invalid_recipient_raises(
    journal: Journal, fake_gmail: FakeGmailClient, benign_llm
) -> None:
    with pytest.raises(ValueError):
        handle_send_email(
            SendEmailInput(to="not-an-email", subject="s", body="b", context=None),
            model=benign_llm,
            gmail=fake_gmail,
            journal=journal,
            domain="general",
        )


def test_gmail_auth_failure_is_structured_error_not_crash(journal: Journal, benign_llm) -> None:
    failing_gmail = FakeGmailClient(fail_with=GmailAuthError("not authed"))
    result = handle_send_email(
        SendEmailInput(to="alice@example.com", subject="s", body="Hi.", context=None),
        model=benign_llm,
        gmail=failing_gmail,
        journal=journal,
        domain="general",
    )
    assert result["decision"] == "hold"
    assert result["error"] is not None
    assert "auth" in result["error"].lower()

    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    assert rec.user_choice == "send_failed"


def test_wisdom_frame_json_in_journal_is_parseable(
    journal: Journal, fake_gmail: FakeGmailClient, benign_llm
) -> None:
    result = handle_send_email(
        SendEmailInput(to="alice@example.com", subject="s", body="Hello.", context=None),
        model=benign_llm,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )
    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    parsed = json.loads(rec.wisdom_frame_json)
    assert parsed["sensitivity_level"] == "low"


def test_always_frames_even_trivial_email(
    journal: Journal, fake_gmail: FakeGmailClient, benign_llm
) -> None:
    """Policy: every email send runs the framing pass. Never skip it based on length
    or content heuristics. If this test ever fails, the policy has been violated.
    """
    result = handle_send_email(
        SendEmailInput(to="alice@example.com", subject="hi", body=".", context=None),
        model=benign_llm,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )
    # If framing was skipped, the LLM would not have been invoked and
    # `wisdom_frame` would be the static fallback. Confirm the benign fixture's
    # emotional_context string is present.
    assert result["wisdom_frame"]["emotional_context"] == "routine"


def test_invalid_recipient_leaves_journal_empty(
    journal: Journal, fake_gmail: FakeGmailClient, benign_llm
) -> None:
    """Invariant: validation failures never write a journal row. The handler
    constructs ``EmailToSend`` before framing precisely to preserve this."""
    with pytest.raises(ValueError):
        handle_send_email(
            SendEmailInput(to="", subject="s", body="b", context=None),
            model=benign_llm,
            gmail=fake_gmail,
            journal=journal,
            domain="general",
        )
    assert journal.list() == []


def test_framing_fallback_path_on_llm_error(journal: Journal, fake_gmail: FakeGmailClient) -> None:
    """When the framing LLM call raises, the orchestrator recovers via the
    static fallback frame and still completes the flow with a journaled pause.
    The fallback frame is_consequential=True; the gate then tries to build a
    revision and (the same failing model) also raises, so the gate returns
    hold. No send is attempted. No crash reaches the caller."""
    from unittest.mock import MagicMock

    failing_model = MagicMock()
    failing_model.invoke.side_effect = RuntimeError("LLM API down")

    result = handle_send_email(
        SendEmailInput(to="alice@example.com", subject="s", body="Hello.", context=None),
        model=failing_model,
        gmail=fake_gmail,
        journal=journal,
        domain="general",
    )

    assert result["journal_entry_id"] is not None
    assert result["decision"] == "hold"
    assert len(fake_gmail.sent) == 0

    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    assert rec.decision == "hold"


def test_gmail_send_error_is_structured(journal: Journal, benign_llm) -> None:
    """Parallel to the auth-error case: a transport-level Gmail failure must
    be surfaced as a structured ``hold`` decision with an error message, and
    the journal row must record ``send_failed``."""
    from bodhisattva_mcp.gmail_client import GmailSendError

    failing_gmail = FakeGmailClient(fail_with=GmailSendError("Gmail 503"))
    result = handle_send_email(
        SendEmailInput(to="alice@example.com", subject="s", body="Hi.", context=None),
        model=benign_llm,
        gmail=failing_gmail,
        journal=journal,
        domain="general",
    )

    assert result["decision"] == "hold"
    assert result["error"] is not None
    assert "Gmail 503" in result["error"] or "gmail" in result["error"].lower()

    rec = journal.get(result["journal_entry_id"])
    assert rec is not None
    assert rec.user_choice == "send_failed"
