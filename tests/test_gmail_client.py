"""Tests for the Gmail client — focusing on the Protocol and the Fake.

The real GoogleGmailClient is exercised manually against a real Gmail
account before launch; we do not mock the Google SDK in automated tests.
"""

import pytest

from bodhisattva_mcp.gmail_client import (
    EmailToSend,
    FakeGmailClient,
    GmailAuthError,
    GmailClient,
)


def test_fake_send_records_calls_and_returns_message_id() -> None:
    fake = FakeGmailClient()
    msg_id = fake.send(
        EmailToSend(
            to="alice@example.com",
            subject="Hi",
            body="Body.",
        )
    )
    assert msg_id.startswith("fake-")
    assert len(fake.sent) == 1
    assert fake.sent[0].to == "alice@example.com"
    assert fake.sent[0].subject == "Hi"


def test_fake_can_simulate_auth_error() -> None:
    fake = FakeGmailClient(fail_with=GmailAuthError("not authorized"))
    with pytest.raises(GmailAuthError):
        fake.send(EmailToSend(to="x@y.z", subject="s", body="b"))


def test_fake_conforms_to_protocol() -> None:
    """FakeGmailClient must satisfy the GmailClient Protocol."""
    fake: GmailClient = FakeGmailClient()
    assert callable(getattr(fake, "send", None))


def test_email_to_send_requires_minimal_fields() -> None:
    # No raise for well-formed input.
    EmailToSend(to="x@y.z", subject="s", body="b")

    # Empty recipient rejected.
    with pytest.raises(ValueError):
        EmailToSend(to="", subject="s", body="b")

    # Missing @ rejected.
    with pytest.raises(ValueError):
        EmailToSend(to="not-an-email", subject="s", body="b")
