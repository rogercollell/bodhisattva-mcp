# Contributing to bodhisattva-mcp

Thanks for your interest. This is a small, opinionated project — read this
before you open a substantial PR.

## Scope

v0.1 is intentionally narrow: one MCP tool (`bodhisattva.send_email`), a
local journal, and a localhost web UI. Features outside that scope belong
in a future milestone:

- **v0.2 (planned):** hosted memory-aware framing + paid subscription.
- **v0.3+:** additional wrappers (Slack, Outlook, ...) as demand dictates.

If you have an idea that expands scope, please open an issue for discussion
**before** writing code.

## Development setup

```bash
git clone https://github.com/rogercollell/bodhisattva-mcp
cd bodhisattva-mcp
uv sync --all-groups
```

## Running tests

```bash
uv run pytest
```

The eval suite exercises the wisdom-framing prompt against 30 fixture
drafts. It hits the LLM provider, so it needs a real API key:

```bash
ANTHROPIC_API_KEY=sk-ant-... uv run python tests/evals/run_eval.py
```

## Linting and formatting

This project uses ruff for both. CI blocks merges on either check failing:

```bash
uv run ruff check .
uv run ruff format --check .
```

Run `uv run ruff format .` to auto-format.

## Commit style

Conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `chore:`, `ci:`).
Scope in parens when useful: `feat(server): ...`, `docs(install): ...`.

## Pull requests

- One change per PR; keep them small and revertable.
- Link to the issue the PR closes (use `Closes #NN`).
- Fill in the PR template checklist.
- CI must be green.

## Security

See [SECURITY.md](SECURITY.md) if it exists — otherwise, report security
issues privately to the maintainer listed in `pyproject.toml`, not via a
public issue.
