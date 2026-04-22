"""Tests for the --version flag on the CLI entrypoint."""

from __future__ import annotations

import subprocess
import sys


def test_version_flag_prints_version() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "bodhisattva_mcp", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    # Output should look like "bodhisattva-mcp <version>"
    assert "bodhisattva-mcp" in result.stdout
    # Version string should contain at least one digit (e.g., "0.1.0")
    assert any(ch.isdigit() for ch in result.stdout)
