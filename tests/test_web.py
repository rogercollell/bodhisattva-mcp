"""Tests for the local journal web UI."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bodhisattva_mcp.journal import Journal, PauseRecord
from bodhisattva_mcp.web.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    journal = Journal(tmp_path / "journal.sqlite")
    journal.create(
        PauseRecord(
            draft="Alice, this is unreasonable.",
            subject="Q3 deadline",
            recipient="alice@company.com",
            recipient_context="manager",
            wisdom_frame_json='{"sensitivity_level":"high","is_consequential":true}',
            decision="revise",
        )
    )
    app = create_app(journal=journal, settings_summary={"provider": "anthropic", "model": "x"})
    return TestClient(app)


def test_index_lists_pauses(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Q3 deadline" in resp.text
    assert "alice@company.com" in resp.text
    assert "revise" in resp.text


def test_pause_detail_page(client: TestClient) -> None:
    resp = client.get("/p/1")
    assert resp.status_code == 200
    assert "Alice, this is unreasonable." in resp.text
    assert "sensitivity_level" in resp.text


def test_pause_detail_404(client: TestClient) -> None:
    resp = client.get("/p/99999")
    assert resp.status_code == 404


def test_settings_shows_provider(client: TestClient) -> None:
    resp = client.get("/settings")
    assert resp.status_code == 200
    assert "anthropic" in resp.text


def test_index_empty(tmp_path: Path) -> None:
    journal = Journal(tmp_path / "empty.sqlite")
    app = create_app(journal=journal, settings_summary={"provider": "anthropic", "model": "x"})
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "No pauses yet" in resp.text
