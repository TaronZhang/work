"""FastAPI application entry point."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.db.database import async_session, close_db, init_db
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

    # Load persisted config from DB (with decryption)
    from app.routers.config import load_config_from_db

    async with async_session() as db:
        overrides = await load_config_from_db(db)
        settings.apply_overrides(overrides)

    # Ensure data directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    yield
    await close_db()


app = FastAPI(
    title="Bid Info Extractor",
    description="标书信息提取与应答系统 — 导入招标文件，自动提取关键信息、生成应答文件、同步飞书日历",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware (for external API access)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (resolve relative to this file)
_static_dir = str(Path(__file__).parent / "static")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

# Page routes
app.include_router(pages.router)

# API routes
app.include_router(documents.router)
app.include_router(extraction.router)
app.include_router(config.router)
app.include_router(calendar.router)

# External API (with Bearer token auth — created in Phase 2)
try:
    from app.routers.external import router as external_router

    app.include_router(external_router)
except ImportError:
    pass
