# Journal Read Tools Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship bodhisattva-mcp v0.2 — two new MCP tools (`bodhisattva.journal_read`, `bodhisattva.journal_list`) that let other agents (and future-Claude) read past wisdom-pauses, with no changes to the framing loop or the `WisdomFrame` schema.

**Architecture:** The journal layer ([src/bodhisattva_mcp/journal.py](../../../src/bodhisattva_mcp/journal.py)) gains two new optional filters on its existing `list()` method (`decision`, `since`). Two new tool handler modules under `src/bodhisattva_mcp/tools/` mirror the pattern of [tools/send_email.py](../../../src/bodhisattva_mcp/tools/send_email.py): dataclass input, keyword-only deps, dict return. The MCP server ([src/bodhisattva_mcp/server.py](../../../src/bodhisattva_mcp/server.py)) registers them alongside `send_email`. JSON-blob parsing of `wisdom_frame_json` lives in the handlers, not the journal — journal stays a thin SQL wrapper.

**Tech Stack:** Python 3.12, `mcp` SDK, hand-rolled SQLite (stdlib `sqlite3`), pytest, uv.

**Spec reference:** [docs/superpowers/specs/2026-05-17-journal-read-tools-design.md](../specs/2026-05-17-journal-read-tools-design.md)

---

## Task 1: Extend `Journal.list()` with `decision` and `since` filters

**Files:**
- Modify: `src/bodhisattva_mcp/journal.py`
- Test: `tests/test_journal.py`

- [ ] **Step 1: Write failing test for `decision` filter**

Append to `tests/test_journal.py`:

```python
def test_list_by_decision(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="a", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="b", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="hold",
        )
    )
    journal.create(
        PauseRecord(
            draft="c", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="hold",
        )
    )

    holds = journal.list(limit=10, decision="hold")
    assert len(holds) == 2
    assert all(r.decision == "hold" for r in holds)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_journal.py::test_list_by_decision -v`

Expected: FAIL with `TypeError: list() got an unexpected keyword argument 'decision'`

- [ ] **Step 3: Write failing test for `since` filter**

Append to `tests/test_journal.py`:

```python
def test_list_since_excludes_older(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="old", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="proceed",
            timestamp="2026-01-01T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="new", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="proceed",
            timestamp="2026-06-01T00:00:00+00:00",
        )
    )

    recent = journal.list(limit=10, since="2026-03-01T00:00:00+00:00")
    assert len(recent) == 1
    assert recent[0].draft == "new"
```

- [ ] **Step 4: Write failing test for combined filters**

Append to `tests/test_journal.py`:

```python
def test_list_combined_filters(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="1", subject="s", recipient="alice@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="proceed",
            timestamp="2026-04-01T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="2", subject="s", recipient="alice@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="hold",
            timestamp="2026-04-15T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="3", subject="s", recipient="bob@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="hold",
            timestamp="2026-04-20T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="4", subject="s", recipient="alice@x.com", recipient_context=None,
            wisdom_frame_json="{}", decision="hold",
            timestamp="2026-01-01T00:00:00+00:00",
        )
    )

    matches = journal.list(
        limit=10,
        recipient="alice@x.com",
        decision="hold",
        since="2026-02-01T00:00:00+00:00",
    )
    assert len(matches) == 1
    assert matches[0].draft == "2"
```

- [ ] **Step 5: Run all three new tests to confirm they fail**

Run: `uv run pytest tests/test_journal.py::test_list_by_decision tests/test_journal.py::test_list_since_excludes_older tests/test_journal.py::test_list_combined_filters -v`

Expected: All three FAIL with `TypeError: list() got an unexpected keyword argument`.

- [ ] **Step 6: Rewrite `Journal.list()` to support all three filters**

In `src/bodhisattva_mcp/journal.py`, replace the existing `list()` method (currently around lines 88–99) with:

```python
    def list(
        self,
        limit: int = 50,
        recipient: str | None = None,
        decision: str | None = None,
        since: str | None = None,
    ) -> list[PauseRecord]:
        clauses: list[str] = []
        params: list = []
        if recipient is not None:
            clauses.append("recipient = ?")
            params.append(recipient)
        if decision is not None:
            clauses.append("decision = ?")
            params.append(decision)
        if since is not None:
            clauses.append("timestamp >= ?")
            params.append(since)

        query = "SELECT * FROM pauses"
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [_row_to_record(row) for row in rows]
```

- [ ] **Step 7: Run the full journal test file**

Run: `uv run pytest tests/test_journal.py -v`

Expected: All tests PASS, including the existing `test_list_by_recipient` and `test_list_returns_newest_first` (the rewrite must be backward compatible).

- [ ] **Step 8: Run lint and format check**

Run: `uv run ruff check src/bodhisattva_mcp/journal.py tests/test_journal.py && uv run ruff format --check src/bodhisattva_mcp/journal.py tests/test_journal.py`

If format fails, run: `uv run ruff format src/bodhisattva_mcp/journal.py tests/test_journal.py`

- [ ] **Step 9: Commit**

```bash
git add src/bodhisattva_mcp/journal.py tests/test_journal.py
git commit -m "$(cat <<'EOF'
feat(journal): add decision and since filters to list()

Extends Journal.list() with two optional filters used by the upcoming
journal_list MCP tool. Hand-rolled WHERE-clause builder; existing
recipient/limit behavior unchanged. Backed by the existing timestamp
and recipient indexes.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement `bodhisattva.journal_read` tool handler

**Files:**
- Create: `src/bodhisattva_mcp/tools/journal_read.py`
- Test: `tests/test_journal_read_tool.py`

- [ ] **Step 1: Write failing happy-path test**

Create `tests/test_journal_read_tool.py`:

```python
"""Tests for the journal_read tool handler."""

from __future__ import annotations

import json

from bodhisattva_mcp.journal import Journal, PauseRecord
from bodhisattva_mcp.tools.journal_read import JournalReadInput, handle_journal_read


def test_returns_record_with_parsed_wisdom_frame(journal: Journal) -> None:
    frame = {
        "emotional_context": "routine",
        "sensitivity_level": "low",
        "is_consequential": False,
        "consequential_reason": None,
        "wellbeing_risk": False,
        "affected_parties": ["user"],
        "recommended_posture": "steady",
        "guidance": "ordinary send",
        "reflection_invitation": None,
    }
    rec_id = journal.create(
        PauseRecord(
            draft="d", subject="Hello", recipient="r@x.com",
            recipient_context="acquaintance",
            wisdom_frame_json=json.dumps(frame),
            decision="proceed",
        )
    )

    result = handle_journal_read(JournalReadInput(id=rec_id), journal=journal)

    assert result["found"] is True
    record = result["record"]
    assert record["id"] == rec_id
    assert record["decision"] == "proceed"
    assert record["subject"] == "Hello"
    assert record["recipient"] == "r@x.com"
    assert record["recipient_context"] == "acquaintance"
    assert record["wisdom_frame"] == frame
    assert "wisdom_frame_parse_error" not in record


def test_missing_id_returns_not_found(journal: Journal) -> None:
    result = handle_journal_read(JournalReadInput(id=99999), journal=journal)
    assert result == {"found": False, "id": 99999}


def test_malformed_wisdom_frame_json_is_reported(journal: Journal) -> None:
    rec_id = journal.create(
        PauseRecord(
            draft="d", subject="s", recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json="not valid json {",
            decision="proceed",
        )
    )

    result = handle_journal_read(JournalReadInput(id=rec_id), journal=journal)

    assert result["found"] is True
    assert result["record"]["wisdom_frame"] is None
    assert result["record"]["wisdom_frame_parse_error"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_journal_read_tool.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'bodhisattva_mcp.tools.journal_read'`.

- [ ] **Step 3: Create the handler module**

Create `src/bodhisattva_mcp/tools/journal_read.py`:

```python
"""MCP tool: fetch one journal entry by id with parsed wisdom frame."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from bodhisattva_mcp.journal import Journal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JournalReadInput:
    id: int


def handle_journal_read(inp: JournalReadInput, *, journal: Journal) -> dict[str, Any]:
    record = journal.get(inp.id)
    if record is None:
        return {"found": False, "id": inp.id}

    wisdom_frame: dict[str, Any] | None
    parse_error = False
    try:
        wisdom_frame = json.loads(record.wisdom_frame_json)
    except json.JSONDecodeError:
        logger.warning(
            "Malformed wisdom_frame_json in journal entry %s", record.id
        )
        wisdom_frame = None
        parse_error = True

    payload_record: dict[str, Any] = {
        "id": record.id,
        "timestamp": record.timestamp,
        "draft": record.draft,
        "subject": record.subject,
        "recipient": record.recipient,
        "recipient_context": record.recipient_context,
        "decision": record.decision,
        "wisdom_frame": wisdom_frame,
        "user_choice": record.user_choice,
        "final_sent_text": record.final_sent_text,
        "message_id": record.message_id,
    }
    if parse_error:
        payload_record["wisdom_frame_parse_error"] = True

    return {"found": True, "record": payload_record}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_journal_read_tool.py -v`

Expected: All three tests PASS.

- [ ] **Step 5: Run lint and format check**

Run: `uv run ruff check src/bodhisattva_mcp/tools/journal_read.py tests/test_journal_read_tool.py && uv run ruff format --check src/bodhisattva_mcp/tools/journal_read.py tests/test_journal_read_tool.py`

If format fails, run: `uv run ruff format src/bodhisattva_mcp/tools/journal_read.py tests/test_journal_read_tool.py`

- [ ] **Step 6: Commit**

```bash
git add src/bodhisattva_mcp/tools/journal_read.py tests/test_journal_read_tool.py
git commit -m "$(cat <<'EOF'
feat(tools): add journal_read handler

Fetches one journal entry by id; parses wisdom_frame_json into a dict
so callers don't double-parse. Not-found returns {found: false, id};
malformed stored JSON is surfaced via wisdom_frame_parse_error rather
than raising.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Implement `bodhisattva.journal_list` tool handler

**Files:**
- Create: `src/bodhisattva_mcp/tools/journal_list.py`
- Test: `tests/test_journal_list_tool.py`

- [ ] **Step 1: Write failing test for slim-row shape + snippet truncation**

Create `tests/test_journal_list_tool.py`:

```python
"""Tests for the journal_list tool handler."""

from __future__ import annotations

import json

from bodhisattva_mcp.journal import Journal, PauseRecord
from bodhisattva_mcp.tools.journal_list import JournalListInput, handle_journal_list


def _make_frame(sensitivity: str = "low", guidance: str = "fine") -> str:
    return json.dumps(
        {
            "emotional_context": "routine",
            "sensitivity_level": sensitivity,
            "is_consequential": False,
            "consequential_reason": None,
            "wellbeing_risk": False,
            "affected_parties": ["user"],
            "recommended_posture": "steady",
            "guidance": guidance,
            "reflection_invitation": None,
        }
    )


def test_returns_slim_rows_with_snippet_and_sensitivity(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="d", subject="Hello", recipient="r@x.com",
            recipient_context=None,
            wisdom_frame_json=_make_frame(sensitivity="high", guidance="A" * 300),
            decision="revise",
        )
    )

    result = handle_journal_list(JournalListInput(), journal=journal)

    assert "records" in result
    assert len(result["records"]) == 1
    row = result["records"][0]
    assert row["recipient"] == "r@x.com"
    assert row["subject"] == "Hello"
    assert row["decision"] == "revise"
    assert row["sensitivity_level"] == "high"
    assert row["guidance_snippet"] == "A" * 200
    assert len(row["guidance_snippet"]) == 200
    # Slim row must NOT contain draft or full wisdom_frame.
    assert "draft" not in row
    assert "wisdom_frame" not in row
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_journal_list_tool.py::test_returns_slim_rows_with_snippet_and_sensitivity -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'bodhisattva_mcp.tools.journal_list'`.

- [ ] **Step 3: Create the handler module**

Create `src/bodhisattva_mcp/tools/journal_list.py`:

```python
"""MCP tool: list past wisdom-pauses with optional filters."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from bodhisattva_mcp.journal import Journal, PauseRecord

logger = logging.getLogger(__name__)

_VALID_DECISIONS = frozenset({"proceed", "revise", "hold"})
_DEFAULT_LIMIT = 50
_MIN_LIMIT = 1
_MAX_LIMIT = 200
_SNIPPET_LEN = 200


@dataclass(frozen=True)
class JournalListInput:
    recipient: str | None = None
    decision: str | None = None
    since: str | None = None
    limit: int = _DEFAULT_LIMIT


def handle_journal_list(inp: JournalListInput, *, journal: Journal) -> dict[str, Any]:
    if inp.decision is not None and inp.decision not in _VALID_DECISIONS:
        return {
            "error": "invalid decision: must be one of proceed | revise | hold",
            "code": "invalid_argument",
        }
    if inp.since is not None:
        try:
            datetime.fromisoformat(inp.since)
        except ValueError:
            return {
                "error": "invalid since: must be an ISO 8601 timestamp",
                "code": "invalid_argument",
            }

    limit = max(_MIN_LIMIT, min(_MAX_LIMIT, inp.limit))

    records = journal.list(
        limit=limit,
        recipient=inp.recipient,
        decision=inp.decision,
        since=inp.since,
    )
    return {"records": [_to_slim(r) for r in records]}


def _to_slim(record: PauseRecord) -> dict[str, Any]:
    sensitivity_level: str | None = None
    guidance_snippet = ""
    try:
        frame = json.loads(record.wisdom_frame_json)
    except json.JSONDecodeError:
        logger.warning(
            "Malformed wisdom_frame_json in journal entry %s", record.id
        )
    else:
        raw_level = frame.get("sensitivity_level")
        if isinstance(raw_level, str):
            sensitivity_level = raw_level
        raw_guidance = frame.get("guidance", "")
        if isinstance(raw_guidance, str):
            guidance_snippet = raw_guidance[:_SNIPPET_LEN].rstrip()

    return {
        "id": record.id,
        "timestamp": record.timestamp,
        "recipient": record.recipient,
        "subject": record.subject,
        "decision": record.decision,
        "sensitivity_level": sensitivity_level,
        "guidance_snippet": guidance_snippet,
        "user_choice": record.user_choice,
    }
```

- [ ] **Step 4: Run the first test to verify it passes**

Run: `uv run pytest tests/test_journal_list_tool.py::test_returns_slim_rows_with_snippet_and_sensitivity -v`

Expected: PASS.

- [ ] **Step 5: Add tests for filter combinations**

Append to `tests/test_journal_list_tool.py`:

```python
def test_filter_by_recipient(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="a", subject="s", recipient="alice@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="b", subject="s", recipient="bob@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="proceed",
        )
    )

    result = handle_journal_list(
        JournalListInput(recipient="alice@x.com"), journal=journal
    )
    assert len(result["records"]) == 1
    assert result["records"][0]["recipient"] == "alice@x.com"


def test_filter_by_decision(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="a", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="b", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="hold",
        )
    )

    result = handle_journal_list(
        JournalListInput(decision="hold"), journal=journal
    )
    assert len(result["records"]) == 1
    assert result["records"][0]["decision"] == "hold"


def test_filter_by_since(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="old", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="proceed",
            timestamp="2026-01-01T00:00:00+00:00",
        )
    )
    journal.create(
        PauseRecord(
            draft="new", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(), decision="proceed",
            timestamp="2026-06-01T00:00:00+00:00",
        )
    )

    result = handle_journal_list(
        JournalListInput(since="2026-03-01T00:00:00+00:00"), journal=journal
    )
    assert len(result["records"]) == 1
    assert result["records"][0]["timestamp"].startswith("2026-06")
```

- [ ] **Step 6: Add tests for input validation**

Append to `tests/test_journal_list_tool.py`:

```python
def test_invalid_decision_returns_error(journal: Journal) -> None:
    result = handle_journal_list(
        JournalListInput(decision="bogus"), journal=journal
    )
    assert result["code"] == "invalid_argument"
    assert "decision" in result["error"]
    assert "records" not in result


def test_invalid_since_returns_error(journal: Journal) -> None:
    result = handle_journal_list(
        JournalListInput(since="not-a-date"), journal=journal
    )
    assert result["code"] == "invalid_argument"
    assert "since" in result["error"]
    assert "records" not in result
```

- [ ] **Step 7: Add tests for limit clamping**

Append to `tests/test_journal_list_tool.py`:

```python
def test_limit_clamps_low(journal: Journal) -> None:
    for i in range(3):
        journal.create(
            PauseRecord(
                draft=f"d{i}", subject="s", recipient="r@x.com",
                recipient_context=None,
                wisdom_frame_json=_make_frame(), decision="proceed",
            )
        )

    # limit=0 clamps to 1
    result = handle_journal_list(JournalListInput(limit=0), journal=journal)
    assert len(result["records"]) == 1

    # negative clamps to 1
    result = handle_journal_list(JournalListInput(limit=-5), journal=journal)
    assert len(result["records"]) == 1


def test_limit_clamps_high(journal: Journal) -> None:
    for i in range(5):
        journal.create(
            PauseRecord(
                draft=f"d{i}", subject="s", recipient="r@x.com",
                recipient_context=None,
                wisdom_frame_json=_make_frame(), decision="proceed",
            )
        )

    # limit=9999 is accepted but only 5 rows exist
    result = handle_journal_list(JournalListInput(limit=9999), journal=journal)
    assert len(result["records"]) == 5
```

- [ ] **Step 8: Add test for malformed-row resilience**

Append to `tests/test_journal_list_tool.py`:

```python
def test_one_malformed_row_does_not_poison_list(journal: Journal) -> None:
    journal.create(
        PauseRecord(
            draft="good", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json=_make_frame(sensitivity="medium", guidance="all fine"),
            decision="proceed",
        )
    )
    journal.create(
        PauseRecord(
            draft="bad", subject="s", recipient="r@x.com", recipient_context=None,
            wisdom_frame_json="not valid json",
            decision="hold",
        )
    )

    result = handle_journal_list(JournalListInput(), journal=journal)
    assert len(result["records"]) == 2

    bad_row = next(r for r in result["records"] if r["decision"] == "hold")
    assert bad_row["sensitivity_level"] is None
    assert bad_row["guidance_snippet"] == ""

    good_row = next(r for r in result["records"] if r["decision"] == "proceed")
    assert good_row["sensitivity_level"] == "medium"
    assert good_row["guidance_snippet"] == "all fine"
```

- [ ] **Step 9: Run the full test file**

Run: `uv run pytest tests/test_journal_list_tool.py -v`

Expected: All eight tests PASS.

- [ ] **Step 10: Run lint and format check**

Run: `uv run ruff check src/bodhisattva_mcp/tools/journal_list.py tests/test_journal_list_tool.py && uv run ruff format --check src/bodhisattva_mcp/tools/journal_list.py tests/test_journal_list_tool.py`

If format fails, run: `uv run ruff format src/bodhisattva_mcp/tools/journal_list.py tests/test_journal_list_tool.py`

- [ ] **Step 11: Commit**

```bash
git add src/bodhisattva_mcp/tools/journal_list.py tests/test_journal_list_tool.py
git commit -m "$(cat <<'EOF'
feat(tools): add journal_list handler

Lists past wisdom-pauses newest-first with optional filters (recipient,
decision, since) and silent limit clamping to [1, 200]. Projects to slim
rows with sensitivity_level and a 200-char guidance snippet pulled from
wisdom_frame_json. Validates decision and since up-front; one bad row
won't poison the list.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Register tools in MCP server + integration tests

**Files:**
- Modify: `src/bodhisattva_mcp/server.py`
- Test: `tests/test_server.py`

- [ ] **Step 1: Write failing registry test**

Append to `tests/test_server.py`:

```python
def test_registry_exposes_journal_read(registry: dict) -> None:
    assert "bodhisattva.journal_read" in registry


def test_registry_exposes_journal_list(registry: dict) -> None:
    assert "bodhisattva.journal_list" in registry
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_server.py::test_registry_exposes_journal_read tests/test_server.py::test_registry_exposes_journal_list -v`

Expected: Both FAIL with `KeyError` or `AssertionError`.

- [ ] **Step 3: Add server-side constants and registration**

In `src/bodhisattva_mcp/server.py`:

(a) After the existing `_INPUT_SCHEMA` (around line 56), add the constants for the two new tools:

```python
_JOURNAL_READ_NAME = "bodhisattva.journal_read"
_JOURNAL_READ_DESCRIPTION = (
    "Fetch one journal entry by id — the full record of a past wisdom-pause, "
    "including the framing's reasoning (wisdom_frame). Use this to understand "
    "why the framing reached a particular verdict, or to recover context from "
    "a prior send_email call (the id is returned as `journal_entry_id`)."
)
_JOURNAL_READ_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {
            "type": "integer",
            "description": "Journal entry id (from send_email's journal_entry_id or from journal_list).",
        },
    },
    "required": ["id"],
}

_JOURNAL_LIST_NAME = "bodhisattva.journal_list"
_JOURNAL_LIST_DESCRIPTION = (
    "List past wisdom-pauses, newest first, optionally filtered by recipient, "
    "decision, or time. Returns slim rows (id, recipient, subject, decision, "
    "sensitivity_level, short guidance snippet, user_choice). Call "
    "journal_read on a specific id for the full record."
)
_JOURNAL_LIST_SCHEMA = {
    "type": "object",
    "properties": {
        "recipient": {
            "type": ["string", "null"],
            "description": "Exact-match recipient email address.",
        },
        "decision": {
            "type": ["string", "null"],
            "enum": ["proceed", "revise", "hold", None],
            "description": "Filter to one decision type.",
        },
        "since": {
            "type": ["string", "null"],
            "description": "ISO 8601 timestamp; rows at or after this time.",
        },
        "limit": {
            "type": "integer",
            "description": "Max rows (default 50, clamped to 1-200).",
        },
    },
    "required": [],
}
```

(b) Update the imports at the top of the file (around line 29). Replace:

```python
from bodhisattva_mcp.tools.send_email import SendEmailInput, handle_send_email
```

with:

```python
from bodhisattva_mcp.tools.journal_list import JournalListInput, handle_journal_list
from bodhisattva_mcp.tools.journal_read import JournalReadInput, handle_journal_read
from bodhisattva_mcp.tools.send_email import SendEmailInput, handle_send_email
```

(c) Extend `build_tool_registry()` (around lines 59–86). Replace the function body with:

```python
def build_tool_registry(
    *,
    model: BaseChatModel,
    gmail: GmailClient,
    journal: Journal,
    domain: str,
) -> dict[str, Callable[[dict[str, Any]], dict[str, Any]]]:
    """Return a dict mapping tool name -> handler callable.

    Pulled out for tests so we can exercise the handler without the MCP
    transport layer.
    """

    def send_email_handler(args: dict[str, Any]) -> dict[str, Any]:
        return handle_send_email(
            SendEmailInput(
                to=args["to"],
                subject=args["subject"],
                body=args["body"],
                context=args.get("context"),
            ),
            model=model,
            gmail=gmail,
            journal=journal,
            domain=domain,
        )

    def journal_read_handler(args: dict[str, Any]) -> dict[str, Any]:
        return handle_journal_read(
            JournalReadInput(id=args["id"]),
            journal=journal,
        )

    def journal_list_handler(args: dict[str, Any]) -> dict[str, Any]:
        return handle_journal_list(
            JournalListInput(
                recipient=args.get("recipient"),
                decision=args.get("decision"),
                since=args.get("since"),
                limit=args.get("limit", 50),
            ),
            journal=journal,
        )

    return {
        _TOOL_NAME: send_email_handler,
        _JOURNAL_READ_NAME: journal_read_handler,
        _JOURNAL_LIST_NAME: journal_list_handler,
    }
```

(d) Extend `_list_tools()` inside `build_mcp_server()` (around lines 92–100). Replace the return value with:

```python
        return [
            Tool(
                name=_TOOL_NAME,
                description=_TOOL_DESCRIPTION,
                inputSchema=_INPUT_SCHEMA,
            ),
            Tool(
                name=_JOURNAL_READ_NAME,
                description=_JOURNAL_READ_DESCRIPTION,
                inputSchema=_JOURNAL_READ_SCHEMA,
            ),
            Tool(
                name=_JOURNAL_LIST_NAME,
                description=_JOURNAL_LIST_DESCRIPTION,
                inputSchema=_JOURNAL_LIST_SCHEMA,
            ),
        ]
```

- [ ] **Step 4: Run the two new tests to verify they pass**

Run: `uv run pytest tests/test_server.py::test_registry_exposes_journal_read tests/test_server.py::test_registry_exposes_journal_list -v`

Expected: Both PASS.

- [ ] **Step 5: Add dispatch tests**

Append to `tests/test_server.py`:

```python
import json as _json

from bodhisattva_mcp.journal import PauseRecord


def test_journal_read_dispatch_returns_record(registry: dict, tmp_path) -> None:
    # Seed via the journal that the registry's handler closes over.
    # Re-use the same journal path the registry fixture built.
    handler = registry["bodhisattva.journal_read"]
    list_handler = registry["bodhisattva.journal_list"]

    # The registry fixture uses a tmp_path journal; insert a row directly so
    # we have something to read. We re-construct a Journal at the same path.
    # (Simpler: drive the registry by calling send_email first.)
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

    result = handler({"id": entry_id})
    assert result["found"] is True
    assert result["record"]["id"] == entry_id
    assert result["record"]["decision"] == "proceed"

    list_result = list_handler({})
    assert len(list_result["records"]) >= 1
    assert list_result["records"][0]["id"] == entry_id


def test_journal_list_invalid_decision_via_registry(registry: dict) -> None:
    handler = registry["bodhisattva.journal_list"]
    result = handler({"decision": "bogus"})
    assert result["code"] == "invalid_argument"
```

- [ ] **Step 6: Run the full server test file**

Run: `uv run pytest tests/test_server.py -v`

Expected: All tests PASS, including the existing send_email tests.

- [ ] **Step 7: Run the full test suite to confirm nothing regressed**

Run: `uv run pytest -v`

Expected: All tests PASS.

- [ ] **Step 8: Run lint and format check**

Run: `uv run ruff check src/bodhisattva_mcp/server.py tests/test_server.py && uv run ruff format --check src/bodhisattva_mcp/server.py tests/test_server.py`

If format fails, run: `uv run ruff format src/bodhisattva_mcp/server.py tests/test_server.py`

- [ ] **Step 9: Commit**

```bash
git add src/bodhisattva_mcp/server.py tests/test_server.py
git commit -m "$(cat <<'EOF'
feat(server): register journal_read and journal_list MCP tools

Wires the two new tool handlers into build_tool_registry and the
list_tools advertisement. _call_tool is unchanged - dispatch is
registry-driven.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Update privacy doc

**Files:**
- Modify: `docs/privacy.md`

- [ ] **Step 1: Read the current privacy doc**

Run: `cat docs/privacy.md` to confirm structure and find an appropriate insertion point (likely after the existing "What we store locally" section, or wherever the journal is first discussed).

- [ ] **Step 2: Add a paragraph describing the new agent-callable read surface**

Insert the following paragraph into `docs/privacy.md` in the section that describes the local journal (search for the word "journal" to find the right spot). If no journal section exists, add this as a new subsection titled `### Journal read tools (v0.2)`:

```markdown
### Journal read tools (v0.2)

Starting in v0.2, two MCP tools — `bodhisattva.journal_read` and
`bodhisattva.journal_list` — let MCP-aware clients (Claude Desktop, Claude
Code, Cursor, Codex) read the local journal. This widens the in-process
tool surface but **not the data surface**: the journal already exists on
disk, the localhost web UI at `http://localhost:8473` already serves it,
and the calling MCP client is already trusted with `send_email` (which
sees current drafts and writes journal rows). The new tools project the
same data that's already accessible. No data leaves the machine.
```

- [ ] **Step 3: Run lint check on doc (sanity check that nothing else moved)**

Run: `git diff docs/privacy.md`

Expected: a clean diff that only adds the new paragraph/section.

- [ ] **Step 4: Commit**

```bash
git add docs/privacy.md
git commit -m "$(cat <<'EOF'
docs(privacy): document journal read tools surface in v0.2

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Update README, CHANGELOG, and version

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Update the README Status section**

In `README.md`, find the Status block (currently lines 88–93):

```markdown
## Status

- **v0.1 (shipped 2026-04-23):** free tier — one wrap (`send_email`), local
  journal, bring-your-own LLM key.
- **v0.2 (planned):** hosted memory-aware framing + paid subscription.
- **v0.3+:** Slack, Outlook, additional wrappers as demand dictates.
```

Replace it with:

```markdown
## Status

- **v0.1 (shipped 2026-04-23):** free tier — one wrap (`send_email`), local
  journal, bring-your-own LLM key.
- **v0.2 (in development):** journal read tools —
  `bodhisattva.journal_read` and `bodhisattva.journal_list` — expose the
  local journal to MCP-aware agents.
- **v0.3 (planned):** hosted memory-aware framing + paid subscription.
- **v0.4+:** Slack, Outlook, additional wrappers as demand dictates.
```

Note: leave `(in development)`. At ship time the user runs a separate release commit that swaps it for `(shipped YYYY-MM-DD)`, matching how v0.1's date was filled in (commit `009573b`).

- [ ] **Step 2: Update CHANGELOG**

In `CHANGELOG.md`, replace the existing empty `## [Unreleased]` section (line 7) with:

```markdown
## [Unreleased]

### Added
- `bodhisattva.journal_read(id)` MCP tool — fetch one journal entry by id,
  with `wisdom_frame_json` parsed into a nested object.
- `bodhisattva.journal_list(recipient?, decision?, since?, limit?)` MCP
  tool — list past pauses with optional filters; returns slim rows with
  `sensitivity_level` and a 200-char `guidance_snippet`.
- `decision` and `since` filter parameters on `Journal.list()`.

### Changed
- v0.2 was previously planned to be memory-aware framing; that work moves
  to v0.3. v0.2 ships the passive read surface that memory-aware framing
  would have depended on.
```

Note: leave the heading as `## [Unreleased]`. The release step at ship time renames it to `## [0.2.0] - YYYY-MM-DD` (Keep a Changelog convention).

- [ ] **Step 3: Bump version in pyproject.toml**

In `pyproject.toml`, find:

```toml
version = "0.1.0"
```

Replace with:

```toml
version = "0.2.0"
```

- [ ] **Step 4: Run the version flag tests**

Run: `uv run pytest tests/test_version_flag.py -v`

Expected: PASS. The tests use a regex `\d+\.\d+\.\d+` rather than pinning to a specific version, so the bump is transparent — no test update needed.

- [ ] **Step 5: Run the full test suite one more time**

Run: `uv run pytest`

Expected: All tests PASS.

- [ ] **Step 6: Run lint and format check on everything we've touched**

Run: `uv run ruff check . && uv run ruff format --check .`

If format fails, run: `uv run ruff format .`

- [ ] **Step 7: Commit**

```bash
git add README.md CHANGELOG.md pyproject.toml
git commit -m "$(cat <<'EOF'
chore(version): bump to 0.2.0

Journal read tools: bodhisattva.journal_read and bodhisattva.journal_list.
Moves the memory-aware-framing roadmap line to v0.3.

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
EOF
)"
```

Note: do NOT push, tag, or open a PR as part of this plan — release/publish is a separate explicit step the user runs.

---

## Done

All six tasks complete:

1. Journal layer supports the new filters with tests
2. `journal_read` handler with TDD coverage
3. `journal_list` handler with TDD coverage (slim shape, snippet, validation, clamping, resilience)
4. Server registers both tools; dispatch tests cover the happy paths
5. Privacy doc documents the surface change
6. README, CHANGELOG, version all bumped to v0.2.0

Before shipping, the spec calls out two manual sanity checks worth doing once you have a populated journal:

- **Snippet quality:** run `bodhisattva.journal_list` against a journal with real entries and skim the `guidance_snippet` field. If 200 chars consistently feels thin, consider widening to 400 in a follow-up.
- **Agent ergonomics:** drive a manual round-trip from Claude Code — have it `journal_list`, pick a row, `journal_read`, and try to articulate "why this pause happened." If the flow feels stilted, iterate on the tool descriptions before announcing.

Neither sanity check changes code in this plan — they're inputs to whether a follow-up is needed.
