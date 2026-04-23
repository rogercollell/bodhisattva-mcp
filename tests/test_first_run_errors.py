"""Regression tests for first-run error messages.

These tests lock in the specific actionable guidance embedded in each
error, so future refactors can't silently remove it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bodhisattva_mcp.gmail_client import GmailAuthError, GoogleGmailClient


def test_missing_client_secret_error_points_to_install_guide(
    tmp_path: Path,
) -> None:
    creds_path = tmp_path / "credentials.json"  # does not exist
    client_secret_path = tmp_path / "client_secret.json"  # does not exist

    client = GoogleGmailClient(
        credentials_path=creds_path,
        client_secret_path=client_secret_path,
    )

    with pytest.raises(GmailAuthError) as exc_info:
        client._build_service()

    msg = str(exc_info.value)
    assert str(client_secret_path) in msg, "error should include the expected path"
    assert "docs/install.md" in msg, "error should direct user to the install guide"
    assert "Google Cloud" in msg, "error should mention the OAuth provider"


def test_missing_anthropic_api_key_suggests_openai_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    from bodhisattva_mcp.config import Settings

    with pytest.raises(ValueError) as exc_info:
        Settings().build_model()

    msg = str(exc_info.value)
    assert "ANTHROPIC_API_KEY" in msg
    assert "BODHISATTVA_LLM_PROVIDER=openai" in msg, (
        "error should suggest switching to the other provider as a fallback"
    )
    assert "OPENAI_API_KEY" in msg, "error should name the fallback key"


def test_missing_openai_api_key_suggests_anthropic_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    from bodhisattva_mcp.config import Settings

    with pytest.raises(ValueError) as exc_info:
        Settings().build_model()

    msg = str(exc_info.value)
    assert "OPENAI_API_KEY" in msg
    assert "BODHISATTVA_LLM_PROVIDER=anthropic" in msg
    assert "ANTHROPIC_API_KEY" in msg


def test_invalid_provider_lists_valid_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BODHISATTVA_LLM_PROVIDER", "grokster")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "unused")

    from bodhisattva_mcp.config import load_settings

    with pytest.raises(ValueError) as exc_info:
        load_settings()

    msg = str(exc_info.value)
    assert "grokster" in msg, "error should repeat the invalid value"
    assert "anthropic" in msg, "error should list valid options"
    assert "openai" in msg, "error should list valid options"


def test_port_in_use_suggests_env_var_override() -> None:
    import socket

    from bodhisattva_mcp.server import _check_port_available

    # Bind a real socket to occupy a port, then verify the check fails clearly.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))  # let OS pick a free port
        sock.listen(1)
        port = sock.getsockname()[1]

        with pytest.raises(RuntimeError) as exc_info:
            _check_port_available(port)

        msg = str(exc_info.value)
        assert str(port) in msg, "error should include the busy port"
        assert "BODHISATTVA_WEB_PORT" in msg, "error should name the override env var"
