# bodhisattva-mcp

An MCP server that pauses your AI before it sends an email you'll regret.

## What it does

Register a single MCP tool — `bodhisattva.send_email` — that intercepts email
sends from any MCP-compatible agent (Claude Desktop, Claude Code, Cursor,
Codex). For every send, it runs the draft through a wisdom-frame pass that
evaluates emotional context, interpersonal stakes, and whether the draft
would be hard to take back. It then either:

- **proceeds** — sends immediately via Gmail;
- **revises** — returns a suggested rewrite and does not send; or
- **holds** — does not send (critical wellbeing signal or consequential with
  no safe revision).

Every pause is logged to a local SQLite journal. A localhost-only web UI at
`http://localhost:8473` lets you review pauses, see the framing reasoning,
and learn your own patterns.

## Why

AI agents are increasingly capable of consequential action. Existing safety
layers protect infrastructure and budgets. Bodhisattva protects relationships:
it's the `pause` before a regrettable send.

## Install

See [docs/install.md](docs/install.md).

## Privacy

See [docs/privacy.md](docs/privacy.md). Local-first. Your drafts stay on your
machine except for the framing call you chose to route through your LLM
provider.

## Status

- v0.1 (this release): free tier — one wrap (`send_email`), local journal,
  bring-your-own LLM key.
- v0.2 (planned): hosted memory-aware framing + paid subscription.
- v0.3+: Slack, Outlook, additional wrappers as demand dictates.

## License

MIT.
