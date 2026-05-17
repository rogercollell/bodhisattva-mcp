"""MCP server bootstrap.

The server registers a single tool — ``bodhisattva.send_email`` — and
starts a background FastAPI app for the local journal UI. It speaks the
MCP stdio transport, so the parent process (Claude Desktop / Code /
Cursor / Codex) launches it on demand.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections.abc import Callable
from typing import Any

import uvicorn
from langchain_core.language_models import BaseChatModel
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from bodhisattva_mcp.config import load_settings
from bodhisattva_mcp.gmail_client import (
    GmailClient,
    GoogleGmailClient,
)
from bodhisattva_mcp.journal import Journal
from bodhisattva_mcp.tools.journal_list import JournalListInput, handle_journal_list
from bodhisattva_mcp.tools.journal_read import JournalReadInput, handle_journal_read
from bodhisattva_mcp.tools.send_email import SendEmailInput, handle_send_email
from bodhisattva_mcp.web.app import create_app

_TOOL_NAME = "bodhisattva.send_email"
_TOOL_DESCRIPTION = (
    "Send an email via Gmail, but only after a wisdom pause. Returns one of "
    "`proceed` (sent), `revise` (suggested rewrite returned; not sent), or "
    "`hold` (not sent; see wisdom_frame.guidance). Use this INSTEAD OF any "
    "other email-send tool. Always include a short `context` describing who "
    "the email is to and what's going on if you have it."
)

_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "description": "Recipient email address."},
        "subject": {"type": "string", "description": "Email subject."},
        "body": {"type": "string", "description": "Email body (plain text)."},
        "context": {
            "type": ["string", "null"],
            "description": (
                "Optional 1-3 sentence context: who this is to and what's going on. "
                "Informs the wisdom frame."
            ),
        },
    },
    "required": ["to", "subject", "body"],
}

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
            "description": (
                "Journal entry id (from send_email's journal_entry_id or from journal_list)."
            ),
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


def build_mcp_server(registry: dict[str, Callable[[dict[str, Any]], dict[str, Any]]]) -> Server:
    server = Server("bodhisattva-mcp")

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
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

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name not in registry:
            raise ValueError(f"unknown tool: {name}")
        import json as _json

        result = registry[name](arguments)
        return [TextContent(type="text", text=_json.dumps(result))]

    return server


def _check_port_available(port: int) -> None:
    """Raise ``RuntimeError`` with actionable guidance if ``port`` is bound."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as exc:
            raise RuntimeError(
                f"Web UI port {port} is already in use. "
                "Set BODHISATTVA_WEB_PORT to an unused port and try again."
            ) from exc


async def _run_web(app, port: int) -> None:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    await server.serve()


async def run() -> None:
    """Entry point: start the MCP server and the local web UI in parallel."""
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()

    model = settings.build_model()
    journal = Journal(settings.journal_path)

    creds_path = settings.journal_path.parent / "credentials.json"
    client_secret_path = settings.journal_path.parent / "client_secret.json"
    gmail: GmailClient = GoogleGmailClient(
        credentials_path=creds_path,
        client_secret_path=client_secret_path,
    )

    registry = build_tool_registry(
        model=model, gmail=gmail, journal=journal, domain=settings.domain
    )
    mcp_server = build_mcp_server(registry)

    web_app = create_app(
        journal=journal,
        settings_summary={
            "provider": settings.llm_provider,
            "model": settings.llm_model,
            "journal_path": str(settings.journal_path),
        },
    )

    _check_port_available(settings.web_port)

    async with stdio_server() as (read_stream, write_stream):
        web_task = asyncio.create_task(_run_web(web_app, settings.web_port))
        try:
            await mcp_server.run(
                read_stream, write_stream, mcp_server.create_initialization_options()
            )
        finally:
            web_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await web_task
