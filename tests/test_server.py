"""Tests for the MCP server wiring.

We test the tool registration and request handling directly, not the
stdio transport (that is exercised manually against Claude Desktop).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bodhisattva_mcp.gmail_client import FakeGmailClient
from bodhisattva_mcp.journal import Journal
from bodhisattva_mcp.server import build_tool_registry


@pytest.fixture
def registry(tmp_path: Path, benign_llm: MagicMock) -> dict:
    journal = Journal(tmp_path / "journal.sqlite")
    gmail = FakeGmailClient()
    return build_tool_registry(model=benign_llm, gmail=gmail, journal=journal, domain="general")


def test_registry_exposes_send_email(registry: dict) -> None:
    assert "bodhisattva.send_email" in registry


def test_registry_handler_returns_proceed_for_benign(registry: dict) -> None:
    handler = registry["bodhisattva.send_email"]
    result = handler(
        {
            "to": "alice@example.com",
            "subject": "s",
            "body": "benign body",
            "context": None,
        }
    )
    assert result["decision"] == "proceed"


def test_registry_handler_validates_input(registry: dict) -> None:
    handler = registry["bodhisattva.send_email"]
    with pytest.raises(ValueError):
        handler({"to": "", "subject": "s", "body": "b"})


def test_registry_exposes_journal_read(registry: dict) -> None:
    assert "bodhisattva.journal_read" in registry


def test_registry_exposes_journal_list(registry: dict) -> None:
    assert "bodhisattva.journal_list" in registry


def test_journal_read_and_list_dispatch_via_registry(registry: dict) -> None:
    # Seed by calling send_email through the registry, then read and list back.
    send = registry["bodhisattva.send_email"]
    send_result = send(
        {
            "to": "alice@example.com",
            "subject": "Hi",
            "body": "benign body",
            "context": None,
        }
    )
    entry_id = send_result["journal_entry_id"]

    read_handler = registry["bodhisattva.journal_read"]
    read_result = read_handler({"id": entry_id})
    assert read_result["found"] is True
    assert read_result["record"]["id"] == entry_id
    assert read_result["record"]["decision"] == "proceed"

    list_handler = registry["bodhisattva.journal_list"]
    list_result = list_handler({})
    assert len(list_result["records"]) >= 1
    assert list_result["records"][0]["id"] == entry_id


def test_journal_list_invalid_decision_via_registry(registry: dict) -> None:
    handler = registry["bodhisattva.journal_list"]
    result = handler({"decision": "bogus"})
    assert result["code"] == "invalid_argument"
