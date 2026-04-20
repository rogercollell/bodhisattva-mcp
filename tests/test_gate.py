"""Tests for the decision gate."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from bodhisattva_mcp.attune.models import SensitivityLevel, WisdomFrame
from bodhisattva_mcp.gate import Decision, decide


def _frame(**overrides) -> WisdomFrame:
    base = dict(
        emotional_context="c",
        sensitivity_level=SensitivityLevel.low,
        is_consequential=False,
        wellbeing_risk=False,
        affected_parties=["user"],
        recommended_posture="steady",
        guidance="g",
    )
    base.update(overrides)
    return WisdomFrame(**base)


def _stub_model_with_revision(text: str) -> MagicMock:
    model = MagicMock()
    model.invoke.return_value = AIMessage(content=text)
    return model


def test_critical_returns_hold() -> None:
    frame = _frame(sensitivity_level=SensitivityLevel.critical, wellbeing_risk=True)
    outcome = decide(frame, draft="d", model=_stub_model_with_revision("unused"))
    assert outcome.decision == Decision.hold
    assert outcome.suggested_revision is None


def test_wellbeing_risk_returns_hold_even_when_not_critical() -> None:
    frame = _frame(sensitivity_level=SensitivityLevel.medium, wellbeing_risk=True)
    outcome = decide(frame, draft="d", model=_stub_model_with_revision("unused"))
    assert outcome.decision == Decision.hold


def test_consequential_returns_revise_with_suggested_revision() -> None:
    frame = _frame(
        sensitivity_level=SensitivityLevel.high,
        is_consequential=True,
    )
    model = _stub_model_with_revision("Cooler version of the email.")
    outcome = decide(frame, draft="Hot original", model=model)
    assert outcome.decision == Decision.revise
    assert outcome.suggested_revision == "Cooler version of the email."
    model.invoke.assert_called_once()


def test_benign_returns_proceed_without_calling_model() -> None:
    frame = _frame(sensitivity_level=SensitivityLevel.low, is_consequential=False)
    model = _stub_model_with_revision("should-not-be-called")
    outcome = decide(frame, draft="d", model=model)
    assert outcome.decision == Decision.proceed
    assert outcome.suggested_revision is None
    model.invoke.assert_not_called()


def test_revision_model_failure_falls_back_to_hold() -> None:
    frame = _frame(
        sensitivity_level=SensitivityLevel.high,
        is_consequential=True,
    )
    model = MagicMock()
    model.invoke.side_effect = RuntimeError("api down")
    outcome = decide(frame, draft="d", model=model)
    assert outcome.decision == Decision.hold
    assert "could not generate" in (outcome.reason or "").lower()
