"""Tests for the Settings / config loader."""

from pathlib import Path

import pytest

from bodhisattva_mcp.config import Settings


def test_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("BODHISATTVA_JOURNAL_PATH", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "anthropic")

    s = Settings()
    assert s.llm_provider == "anthropic"
    assert s.web_port == 8473
    assert s.journal_path == tmp_path / ".bodhisattva" / "journal.sqlite"


def test_journal_path_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("BODHISATTVA_JOURNAL_PATH", str(tmp_path / "custom.sqlite"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    s = Settings()
    assert s.journal_path == tmp_path / "custom.sqlite"


def test_requires_provider_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(ValueError) as exc:
        Settings().build_model()
    assert "ANTHROPIC_API_KEY" in str(exc.value)


def test_build_model_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.setenv("BODHISATTVA_LLM_MODEL", "claude-haiku-4-5-20251001")

    model = Settings().build_model()
    # langchain-anthropic returns a ChatAnthropic
    assert type(model).__name__ == "ChatAnthropic"


def test_build_model_openai(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("BODHISATTVA_LLM_MODEL", "gpt-4o-mini")

    model = Settings().build_model()
    assert type(model).__name__ == "ChatOpenAI"
