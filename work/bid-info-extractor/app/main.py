from __future__ import annotations

"""FastAPI application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from sqlalchemy import select

from app.config import settings
from app.db.database import async_session, close_db, init_db
from app.db.models import AppConfig
from app.routers import calendar, config, documents, extraction, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Init Jinja2 templates
    templates_dir = Path(__file__).parent / "templates"
    app.state.templates = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
    )

    # Init DB
    await init_db()

    # Load persisted config from DB
    async with async_session() as db:
        result = await db.execute(select(AppConfig))
        rows = result.scalars().all()
        overrides = {row.key: row.value for row in rows if row.value}
        settings.apply_overrides(overrides)

    # Ensure data directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    yield
    await close_db()


app = FastAPI(
    title="Bid Info Extractor",
    description="标书信息提取与应答系统 — 导入招标文件，自动提取关键信息、生成应答文件、同步飞书日历",
    version="1.0.0",
    lifespan=lifespan,
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Page routes
app.include_router(pages.router)

# API routes
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(config.router)
app.include_router(calendar.router)
