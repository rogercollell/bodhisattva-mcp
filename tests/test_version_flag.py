"""Tests for the --version flag on the CLI entrypoint."""

from __future__ import annotations

import re
import subprocess
import sys

_VERSION_RE = re.compile(r"bodhisattva-mcp \d+\.\d+\.\d+(?:[A-Za-z0-9.+-]*)?\s*$")


def _run_version(flag: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "bodhisattva_mcp", flag],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_version_long_flag_prints_semver() -> None:
    result = _run_version("--version")
    assert result.returncode == 0, result.stderr
    assert _VERSION_RE.match(result.stdout), (
        f"stdout does not match expected 'bodhisattva-mcp X.Y.Z' shape: {result.stdout!r}"
    )


def test_version_short_flag_prints_same_output() -> None:
    long_result = _run_version("--version")
    short_result = _run_version("-V")
    assert short_result.returncode == 0, short_result.stderr
    assert short_result.stdout == long_result.stdout
