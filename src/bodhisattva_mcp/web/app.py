"""Local, localhost-only web UI for the Bodhisattva journal."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from bodhisattva_mcp.journal import Journal

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(*, journal: Journal, settings_summary: dict[str, str]) -> FastAPI:
    app = FastAPI(title="Bodhisattva")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        pauses = journal.list(limit=200)
        return templates.TemplateResponse(
            request,
            "index.html",
            {"pauses": pauses},
        )

    @app.get("/p/{pause_id}", response_class=HTMLResponse)
    def pause_detail(request: Request, pause_id: int) -> HTMLResponse:
        rec = journal.get(pause_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="pause not found")
        frame = json.loads(rec.wisdom_frame_json) if rec.wisdom_frame_json else {}
        return templates.TemplateResponse(
            request,
            "pause.html",
            {"pause": rec, "frame": frame},
        )

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"settings": settings_summary},
        )

    return app
