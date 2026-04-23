# bodhisattva-mcp

> The pause before a regrettable send.

![demo placeholder — replaced in Task 13](docs/assets/demo.gif)

An MCP server that intercepts email sends from AI agents (Claude Desktop,
Claude Code, Cursor, Codex) and runs every draft through a wisdom-frame
pass. Depending on what the frame sees, it either:

- **proceeds** — sends immediately via Gmail;
- **revises** — returns a suggested rewrite and does not send; or
- **holds** — does not send (critical wellbeing signal, or consequential with
  no safe revision).

Every pause is logged to a local SQLite journal. A localhost-only web UI at
`http://localhost:8473` lets you review past pauses and see the framing's
reasoning.

## Quickstart

```bash
# 1. Install
uv tool install bodhisattva-mcp

# 2. Drop in your Google Cloud OAuth client secret (see Install guide).
#    Assumes exactly one client_secret_*.json in ~/Downloads — rename manually if you have several.
mkdir -p ~/.bodhisattva && mv ~/Downloads/client_secret_*.json ~/.bodhisattva/client_secret.json

# 3. Configure your LLM provider
export ANTHROPIC_API_KEY=sk-ant-...

# 4. Wire into your MCP client (example: Claude Code)
cat > .mcp.json <<'EOF'
{
  "mcpServers": {
    "bodhisattva": {
      "command": "uvx",
      "args": ["bodhisattva-mcp"]
    }
  }
}
EOF
```

Full setup (Google Cloud OAuth, all MCP clients): [docs/install.md](docs/install.md).

## What it does

Existing AI safety layers protect infrastructure and budgets. Bodhisattva
protects relationships. When an agent tries to send an email on your behalf,
the framing looks at: emotional context, interpersonal stakes, whether the
draft would be hard to take back — and inserts a pause.

You stay in the loop. The agent gets a clear structured response
(`proceed` / `revise` / `hold`) it can act on. The journal at
`http://localhost:8473` lets you see your own patterns over time.

## What it doesn't do (yet)

v0.1 is intentionally narrow:

- **Gmail only.** Slack, Outlook, and other wrappers are v0.3+.
- **No hosted memory.** The framing is stateless: it sees the current draft
  and optional `context` field, not your past conversations. Memory-aware
  framing is v0.2.
- **No Google verification.** You bring your own Google Cloud OAuth app, so
  you're a "test user" of your own app. This is a feature: your drafts
  never touch any server except the LLM provider you chose.

## Privacy

Local-first. Your drafts stay on your machine except for the framing call
you chose to route through your LLM provider. Credentials are stored at
`~/.bodhisattva/` with `0600` permissions. Full details:
[docs/privacy.md](docs/privacy.md).

## Install

Full install guide: [docs/install.md](docs/install.md).

## Status

- **v0.1 (shipped 2026-04-23):** free tier — one wrap (`send_email`), local
  journal, bring-your-own LLM key.
- **v0.2 (planned):** hosted memory-aware framing + paid subscription.
- **v0.3+:** Slack, Outlook, additional wrappers as demand dictates.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Changelog: [CHANGELOG.md](CHANGELOG.md).

## License

MIT — see [LICENSE](LICENSE).
