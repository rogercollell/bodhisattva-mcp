"""Manual eval runner: score the 30-fixture eval set against the live model.

Usage:
    .venv/bin/python -m tests.evals.run_eval

Writes a markdown report to ``tests/evals/latest-report.md`` and prints a
summary table. Uses your configured BODHISATTVA_LLM_PROVIDER + API key.
"""

from __future__ import annotations

import json
from pathlib import Path

from bodhisattva_mcp.config import Settings
from bodhisattva_mcp.gmail_client import FakeGmailClient
from bodhisattva_mcp.journal import Journal
from bodhisattva_mcp.tools.send_email import SendEmailInput, handle_send_email

FIXTURES = Path(__file__).parent / "fixtures.jsonl"
REPORT = Path(__file__).parent / "latest-report.md"


def main() -> None:
    settings = Settings()
    model = settings.build_model()

    tmp_journal = Path("/tmp/bodhisattva-eval-journal.sqlite")
    tmp_journal.unlink(missing_ok=True)
    journal = Journal(tmp_journal)
    gmail = FakeGmailClient()

    rows = []
    correct = 0
    total = 0

    with FIXTURES.open() as f:
        cases = [json.loads(line) for line in f if line.strip()]

    for case in cases:
        result = handle_send_email(
            SendEmailInput(
                to=case["to"],
                subject=case["subject"],
                body=case["body"],
                context=case.get("context"),
            ),
            model=model,
            gmail=gmail,
            journal=journal,
            domain="general",
        )
        actual = result["decision"]
        expected = case["expected"]
        ok = actual == expected
        correct += int(ok)
        total += 1
        rows.append((case["id"], expected, actual, ok, result["wisdom_frame"].get("guidance", "")))

    non_benign = [r for r in rows if r[1] != "proceed"]
    non_benign_correct = sum(1 for r in non_benign if r[3])
    non_benign_rate = non_benign_correct / len(non_benign) if non_benign else 0.0

    lines = ["# Eval report\n", f"Overall: {correct}/{total} ({100 * correct / total:.1f}%)\n"]
    lines.append(
        f"Non-benign slice: {non_benign_correct}/{len(non_benign)} "
        f"({100 * non_benign_rate:.1f}%)\n\n"
    )
    lines.append("| id | expected | actual | ok | guidance |\n")
    lines.append("|---|---|---|---|---|\n")
    for row in rows:
        id_, exp, act, ok, guidance = row
        mark = "✓" if ok else "✗"
        guidance_cell = guidance.replace("|", " ").replace("\n", " ")[:120]
        lines.append(f"| {id_} | {exp} | {act} | {mark} | {guidance_cell} |\n")

    REPORT.write_text("".join(lines))
    print("".join(lines[:4]))
    print(f"Full report: {REPORT}")


if __name__ == "__main__":
    main()
