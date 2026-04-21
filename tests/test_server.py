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
    return build_tool_registry(
        model=benign_llm, gmail=gmail, journal=journal, domain="general"
    )


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
