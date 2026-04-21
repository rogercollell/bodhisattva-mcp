# tests/conftest.py
"""Shared pytest fixtures."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage

from bodhisattva_mcp.gmail_client import FakeGmailClient
from bodhisattva_mcp.journal import Journal


@pytest.fixture
def journal(tmp_path: Path) -> Journal:
    return Journal(tmp_path / "journal.sqlite")


@pytest.fixture
def fake_gmail() -> FakeGmailClient:
    return FakeGmailClient()


def fake_llm_with_frame(frame: dict, revision: str = "Revised body.") -> MagicMock:
    """Return a MagicMock LLM whose first call returns ``frame`` as JSON and
    second call returns ``revision`` as plain text.
    """
    model = MagicMock()
    responses = [
        AIMessage(content=json.dumps(frame)),
        AIMessage(content=revision),
    ]
    model.invoke.side_effect = responses
    return model


@pytest.fixture
def benign_llm() -> MagicMock:
    return fake_llm_with_frame(
        {
            "emotional_context": "routine",
            "sensitivity_level": "low",
            "is_consequential": False,
            "consequential_reason": None,
            "wellbeing_risk": False,
            "affected_parties": ["user"],
            "recommended_posture": "steady",
            "guidance": "ordinary send, nothing to flag",
            "reflection_invitation": None,
        }
    )


@pytest.fixture
def consequential_llm() -> MagicMock:
    return fake_llm_with_frame(
        {
            "emotional_context": "user frustrated with manager",
            "sensitivity_level": "high",
            "is_consequential": True,
            "consequential_reason": "charged email to a manager",
            "wellbeing_risk": False,
            "affected_parties": ["user", "alice@company.com"],
            "recommended_posture": "steady, transparent, non-judgmental",
            "guidance": "Acknowledge the stakes before sending.",
            "reflection_invitation": "Want to pause and shape this carefully?",
        },
        revision="Alice, I want to flag a concern about the Q3 deadline.",
    )


@pytest.fixture
def critical_llm() -> MagicMock:
    return fake_llm_with_frame(
        {
            "emotional_context": "user may be in crisis",
            "sensitivity_level": "critical",
            "is_consequential": False,
            "consequential_reason": None,
            "wellbeing_risk": True,
            "affected_parties": ["user"],
            "recommended_posture": "lead with attunement",
            "guidance": (
                "Acknowledge distress. If you may be in immediate danger or might act on thoughts "
                "of harming yourself or someone else, call or text 988 now, or contact local "
                "emergency services."
            ),
            "reflection_invitation": None,
        }
    )
