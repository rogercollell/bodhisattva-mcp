# Changelog

All notable changes to this project will be documented in this file. The
format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-04-23

Initial public release.

### Added
- `bodhisattva.send_email` MCP tool: intercepts AI email sends, runs the
  draft through a wisdom-frame pass, and either proceeds, revises, or holds.
- Local SQLite journal of every pause at `~/.bodhisattva/journal.sqlite`.
- Localhost-only web UI at `http://localhost:8473` for reviewing pauses
  and current settings.
- Gmail integration via the `gmail.send` scope (least privilege).
  Each user brings their own Google Cloud OAuth app.
- Bring-your-own LLM: supports `anthropic` and `openai` providers via
  `BODHISATTVA_LLM_PROVIDER`.
- `--version` flag on the CLI entrypoint.
- Friendlier first-run errors for: missing `client_secret.json`, missing
  API key for the selected provider, invalid provider value, and web UI
  port already in use.

## [0.1.0a1] - 2026-04-23

Pre-release to claim the PyPI name and verify the publishing pipeline.
Functionally equivalent to 0.1.0.

[Unreleased]: https://github.com/rogercollell/bodhisattva-mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/rogercollell/bodhisattva-mcp/compare/v0.1.0a1...v0.1.0
[0.1.0a1]: https://github.com/rogercollell/bodhisattva-mcp/releases/tag/v0.1.0a1
