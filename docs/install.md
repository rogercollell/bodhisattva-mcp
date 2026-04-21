# Install

## 1. Install `bodhisattva-mcp`

```bash
uv tool install bodhisattva-mcp
```

Or, for development:

```bash
git clone https://github.com/rogercollell/bodhisattva-mcp
cd bodhisattva-mcp
uv sync
```

## 2. Set up Gmail credentials

1. Create an OAuth client ID in Google Cloud Console (type: Desktop application).
2. Download the `client_secret.json` file.
3. Move it to `~/.bodhisattva/client_secret.json` (create the directory if needed).

On first `send_email` call, a browser window will open for OAuth consent. The resulting credentials are cached at `~/.bodhisattva/credentials.json` with `0600` permissions.

## 3. Configure your LLM provider

Bodhisattva uses your own API key on the free tier. Set one of:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

Select the provider:

```bash
export BODHISATTVA_LLM_PROVIDER=anthropic   # or openai
```

## 4. Wire it into your MCP client

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "bodhisattva": {
      "command": "uvx",
      "args": ["bodhisattva-mcp"],
      "env": {
        "ANTHROPIC_API_KEY": "sk-ant-...",
        "BODHISATTVA_LLM_PROVIDER": "anthropic"
      }
    }
  }
}
```

Restart Claude Desktop. Ask it to send an email; Bodhisattva's `send_email` tool will appear in the available tools and Claude will use it instead of any other email tool.

### Claude Code

Add to `.mcp.json` in your project:

```json
{
  "mcpServers": {
    "bodhisattva": {
      "command": "uvx",
      "args": ["bodhisattva-mcp"]
    }
  }
}
```

## 5. View your journal

With the MCP client running, open: http://localhost:8473

Change the port via `BODHISATTVA_WEB_PORT`.
