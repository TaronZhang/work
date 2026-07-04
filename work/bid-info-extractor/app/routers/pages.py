from __future__ import annotations

"""Page routes — Jinja2 template rendering."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return request.app.state.templates.get_template("index.html").render(
        request=request
    )


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    return request.app.state.templates.get_template("documents.html").render(
        request=request
    )


@router.get("/extraction/{project_id}", response_class=HTMLResponse)
async def extraction_page(request: Request, project_id: int):
    return request.app.state.templates.get_template("extraction.html").render(
        request=request, project_id=project_id
    )


@router.get("/calendar", response_class=HTMLResponse)
async def calendar_page(request: Request):
    return request.app.state.templates.get_template("calendar.html").render(
        request=request
    )


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    return request.app.state.templates.get_template("settings.html").render(
        request=request
    )
