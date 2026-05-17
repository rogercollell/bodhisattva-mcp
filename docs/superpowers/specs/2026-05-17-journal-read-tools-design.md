# bodhisattva-mcp v0.2 — Journal Read Tools

**Date:** 2026-05-17
**Status:** Drafted (awaiting approval)
**Target:** Make the existing local journal readable by MCP-aware agents (and future-Claude) through two new tools — `bodhisattva.journal_read` and `bodhisattva.journal_list` — so that "why a change happened" is discoverable beyond the localhost web UI.

## Goal

In v0.1, every email send is journaled with the framing's full reasoning (`emotional_context`, `consequential_reason`, `recommended_posture`, `guidance`, ...), but that data is a one-way street: the framing is stateless and only humans can read the journal via `http://localhost:8473`. v0.2 closes the most basic part of the loop — read-back to agents — by exposing the journal as MCP tools. Another agent (or future-Claude with no fresh context) can now look at a journal entry and reconstruct why the framing reached the verdict it did.

Framing: this is the *passive* half of the journal-as-memory story. The *active* half (framing pass reads past pauses to inform new ones) is deliberately deferred.

## Scope

### In scope
- Two new MCP tools registered in [src/bodhisattva_mcp/server.py](../../src/bodhisattva_mcp/server.py): `bodhisattva.journal_read` and `bodhisattva.journal_list`
- Extending the existing `Journal.list()` in [src/bodhisattva_mcp/journal.py](../../src/bodhisattva_mcp/journal.py) with `decision` and `since` filters
- Two new tool handler modules under `src/bodhisattva_mcp/tools/` (one per tool) mirroring the pattern of `tools/send_email.py`
- Unit tests for the new filters and handlers; integration tests for tool registration and dispatch
- A short paragraph added to `docs/privacy.md` documenting that journal reads are now agent-callable
- README update: move the v0.2 roadmap line ("hosted memory-aware framing") to v0.3, and replace it with the journal read tools description
- CHANGELOG entry + version bump to 0.2.0

### Out of scope (future work)
- Memory-aware framing — the framing pass reading past pauses to inform new ones. Moves to v0.3+
- Recipient-level narrative summaries (the LLM-at-query-time tool from brainstorming option B)
- Semantic search / embeddings / vector store (option C)
- Any change to the localhost web UI
- Any change to the `WisdomFrame` schema or the `pauses` table schema
- New write tools (manual annotation, deletion, redaction)
- Filtering by fields stored inside `wisdom_frame_json` (e.g., `sensitivity_level`) — would require promoting those to columns; defer until a real use case forces it
- Fuzzy / substring search

## Approach: Project, don't reshape

The journal already stores enough to answer "why." The job is to *project* what's there through a small, ergonomic MCP surface — not to redesign the data model. Hand-rolled SQL (matching the comment in `journal.py:5`), no ORM, no new runtime dependencies. The journal layer returns `PauseRecord` objects as today; the tool handlers do JSON-blob parsing and slim projection.

This keeps each layer doing one thing: the journal stores and queries rows; the handler projects rows into the agent-facing shape.

## Components

### 1. Query layer — `src/bodhisattva_mcp/journal.py`

Extend the existing `list()`:

```python
def list(
    self,
    limit: int = 50,
    recipient: str | None = None,
    decision: str | None = None,
    since: str | None = None,
) -> list[PauseRecord]:
    ...
```

- SQL builds `WHERE` clauses dynamically: `recipient = ?`, `decision = ?`, `timestamp >= ?`. Conditions joined with `AND`. `ORDER BY id DESC LIMIT ?` unchanged.
- The existing `idx_pauses_timestamp` covers `since`; the existing `idx_pauses_recipient` covers recipient. `decision` is unindexed — acceptable at this scale (one row per email send).
- `since` is treated as an opaque ISO 8601 string for comparison — SQLite's lexicographic comparison on ISO 8601 strings matches chronological order, so no parsing in the journal layer.
- `get(id)` is reused unchanged for `journal_read`.

### 2. `bodhisattva.journal_read` tool

**New file:** `src/bodhisattva_mcp/tools/journal_read.py`

Input schema:
```json
{
  "type": "object",
  "properties": {
    "id": { "type": "integer", "description": "Journal entry id (from send_email's `journal_entry_id` response, or from journal_list)." }
  },
  "required": ["id"]
}
```

Tool description (shown to agents):
> Fetch one journal entry — the full record of a past wisdom-pause, including the framing's reasoning. Use this to understand why the framing reached a particular verdict, or to recover context from a prior send_email call.

Handler responsibilities:
1. Call `journal.get(id)`.
2. If `None`, return `{"found": false, "id": id}`.
3. Otherwise parse `wisdom_frame_json` into a dict and return:
   ```json
   {
     "found": true,
     "record": {
       "id": 47,
       "timestamp": "2026-05-15T14:23:11+00:00",
       "draft": "...",
       "subject": "...",
       "recipient": "sarah@example.com",
       "recipient_context": "...",
       "decision": "revise",
       "wisdom_frame": { /* full WisdomFrame object as a JSON object, not a string */ },
       "user_choice": "sent",
       "final_sent_text": "...",
       "message_id": "..."
     }
   }
   ```
4. If `wisdom_frame_json` won't parse (rare — only possible if a future bug wrote one): return the record with `"wisdom_frame": null` and `"wisdom_frame_parse_error": true`. Never raise.

### 3. `bodhisattva.journal_list` tool

**New file:** `src/bodhisattva_mcp/tools/journal_list.py`

Input schema:
```json
{
  "type": "object",
  "properties": {
    "recipient": { "type": ["string", "null"], "description": "Filter to pauses with this exact recipient address." },
    "decision":  { "type": ["string", "null"], "enum": ["proceed", "revise", "hold", null] },
    "since":     { "type": ["string", "null"], "description": "ISO 8601 timestamp; only rows at or after this time." },
    "limit":     { "type": "integer", "description": "Max rows to return (default 50, clamped to 1–200)." }
  },
  "required": []
}
```

Tool description (shown to agents):
> List past wisdom-pauses, newest first, optionally filtered by recipient, decision, or time. Returns slim rows (id, recipient, subject, decision, sensitivity_level, short guidance snippet, user_choice). Call journal_read on a specific id for full details.

Handler responsibilities:
1. Validate `decision` — if non-null and not in `{"proceed", "revise", "hold"}`, return `{"error": "invalid decision: must be proceed | revise | hold", "code": "invalid_argument"}`.
2. Validate `since` — if non-null, try `datetime.fromisoformat(since)`. On parse failure return `{"error": "invalid since: must be ISO 8601", "code": "invalid_argument"}`.
3. Clamp `limit` to `[1, 200]` (default 50). Clamping is silent — no error.
4. Call `journal.list(...)`.
5. Project each record to the slim shape:
   ```json
   {
     "id": 47,
     "timestamp": "...",
     "recipient": "...",
     "subject": "...",
     "decision": "revise",
     "sensitivity_level": "high",
     "guidance_snippet": "First ~200 chars of wisdom_frame.guidance...",
     "user_choice": "sent"
   }
   ```
   - `sensitivity_level` and `guidance_snippet` are extracted from `wisdom_frame_json` at projection time. If the JSON won't parse for a given row, fall back to `"sensitivity_level": null, "guidance_snippet": ""` for that row — never fail the whole list.
   - `guidance_snippet` is the first 200 characters of `wisdom_frame.guidance`, with trailing whitespace stripped. No ellipsis added — the caller knows it's a snippet.
6. Return `{"records": [...]}`.

### 4. Server registration — `src/bodhisattva_mcp/server.py`

Add module-level constants alongside the existing `_TOOL_NAME` / `_TOOL_DESCRIPTION` / `_INPUT_SCHEMA`:

- `_JOURNAL_READ_NAME`, `_JOURNAL_READ_DESCRIPTION`, `_JOURNAL_READ_SCHEMA`
- `_JOURNAL_LIST_NAME`, `_JOURNAL_LIST_DESCRIPTION`, `_JOURNAL_LIST_SCHEMA`

Extend `build_tool_registry()` to register two more handlers (closing over `journal` only — neither tool needs `model`, `gmail`, or `domain`).

Extend `_list_tools()` to return all three `Tool` objects.

`_call_tool()` is unchanged — dispatch is already registry-driven.

### 5. Privacy doc update — `docs/privacy.md`

Add a short paragraph: journal read tools are agent-callable, meaning any MCP-aware client wired into bodhisattva can read past pause records. This is in-process (same trust boundary as `send_email`, which already sees current drafts and writes to the same journal) and same data the localhost web UI already exposes. No data leaves the machine.

### 6. README + CHANGELOG + version

- README "Status" section: move "v0.2 (planned): hosted memory-aware framing + paid subscription" to v0.3. Replace v0.2 with "v0.2 (shipped YYYY-MM-DD): journal read tools — `bodhisattva.journal_read` and `bodhisattva.journal_list`, exposing the local journal to MCP-aware agents."
- `CHANGELOG.md`: new `## [0.2.0]` section.
- `pyproject.toml`: bump version to 0.2.0.

## Data flow

```
caller agent
   │
   │ MCP call: bodhisattva.journal_list({recipient: "..."}, ...)
   ▼
server.py: _call_tool
   │
   ▼
tools/journal_list.handle_journal_list
   │  validate inputs (decision, since); clamp limit
   ▼
journal.Journal.list(limit, recipient, decision, since)
   │  hand-rolled SQL, returns list[PauseRecord]
   ▼
back in handler: parse wisdom_frame_json per row → slim projection
   │
   ▼
return {"records": [...]} → JSON-encoded into TextContent → MCP transport
```

`journal_read` is the same shape with `journal.Journal.get(id)` as the bottom call.

## Error handling summary

| Condition | Behavior |
|---|---|
| `journal_read` id not found | `{"found": false, "id": id}` — explicit, not an exception |
| `journal_read` malformed `wisdom_frame_json` in stored row | Return record with `"wisdom_frame": null, "wisdom_frame_parse_error": true` |
| `journal_list` invalid `decision` value | `{"error": "...", "code": "invalid_argument"}` |
| `journal_list` unparseable `since` | `{"error": "...", "code": "invalid_argument"}` |
| `journal_list` `limit` outside `[1, 200]` | Clamped silently |
| `journal_list` one row's `wisdom_frame_json` won't parse | Row included with `sensitivity_level: null, guidance_snippet: ""` |
| Missing required `id` on read | MCP framework rejects via JSON schema |

## Testing

### Unit tests
- `tests/test_journal.py` — extend with:
  - `list(decision="hold")` returns only hold rows
  - `list(since=...)` excludes older rows
  - Combined filters (`recipient` + `decision` + `since`) intersect correctly
  - Ordering remains newest-first
  - Journal layer accepts arbitrary `limit` values verbatim (clamping is the handler's job; the journal layer stays a thin SQL wrapper)

- `tests/test_journal_read_tool.py` *(new, matching the `test_send_email_tool.py` naming pattern)*:
  - Happy path: existing id returns `{found: true, record: {...}}` with parsed wisdom_frame
  - Missing id returns `{found: false}`
  - Row with malformed `wisdom_frame_json` returns `wisdom_frame_parse_error: true`

- `tests/test_journal_list_tool.py` *(new)*:
  - Each filter individually
  - Filter combinations
  - Clamping behavior: limit=0 → 1, limit=9999 → 200, negative → 1, default (omitted) → 50
  - Invalid `decision` → error response
  - Invalid `since` → error response
  - Snippet truncation at 200 chars
  - One row with malformed `wisdom_frame_json` does not poison the list

### Integration tests
- `tests/test_server.py`:
  - `_list_tools` returns three tools with the expected names and descriptions
  - Registry has all three handler entries
  - Dispatch through `_call_tool` works for the two new names; unknown name still raises

## File inventory

| File | Change |
|---|---|
| `src/bodhisattva_mcp/journal.py` | Extend `list()` with `decision` and `since` params |
| `src/bodhisattva_mcp/tools/journal_read.py` | New |
| `src/bodhisattva_mcp/tools/journal_list.py` | New |
| `src/bodhisattva_mcp/server.py` | Register two new tools |
| `tests/test_journal.py` | Add filter tests |
| `tests/test_journal_read_tool.py` | New |
| `tests/test_journal_list_tool.py` | New |
| `tests/test_server.py` | Add registration/dispatch coverage |
| `docs/privacy.md` | Short paragraph on agent-callable journal reads |
| `README.md` | Status section update; mention new tools |
| `CHANGELOG.md` | 0.2.0 entry |
| `pyproject.toml` | Version bump to 0.2.0 |

## Open questions

None at design time. Risks worth re-examining during implementation:

- **Quality of `guidance` snippets.** The whole spec rests on today's `WisdomFrame.guidance` field being substantive enough to make a 200-char preview useful. Sanity-check by running a few real `journal_list` calls against a populated journal before locking the implementation. If snippets read as thin or generic, consider widening to 400 chars or composing the snippet from `guidance` + `consequential_reason`. Schema changes still out of scope.
- **Agent ergonomics.** Once both tools are wired up, do a manual round-trip from Claude Code: have it call `journal_list`, pick a row, call `journal_read`, and try to articulate "why this pause happened." If that flow feels stilted, the tool descriptions or shapes may need iteration before release.
