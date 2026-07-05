"""FastAPI application entry point."""

from __future__ import annotations

import os
import traceback
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader

from app.config import settings
from app.db.database import async_session, close_db, init_db
from app.logger import app_log, error_log, log_error, log_request
from app.routers import calendar, config, documents, extraction, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    app_log.info("=" * 50)
    app_log.info("Bid Info Extractor v2.0.0 starting...")

    # Init Jinja2 templates
    templates_dir = Path(__file__).parent / "templates"
    app.state.templates = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=True,
    )

    # Init DB
    await init_db()
    app_log.info(f"Database: {settings.database_url}")

    # Load persisted config from DB (with decryption)
    from app.routers.config import load_config_from_db

    async with async_session() as db:
        overrides = await load_config_from_db(db)
        settings.apply_overrides(overrides)

    # Ensure data directories exist
    os.makedirs(settings.upload_dir, exist_ok=True)
    os.makedirs(settings.export_dir, exist_ok=True)

    app_log.info(
        f"LLM: {settings.llm_base_url} model={settings.llm_model} "
        f"key={'configured' if settings.llm_api_key else 'MISSING'}"
    )
    app_log.info(
        f"Feishu: app_id={'configured' if settings.feishu_app_id else 'MISSING'}"
    )
    app_log.info(
        f"Encryption: {'ENABLED' if settings._get_encryption_key() else 'DISABLED'}"
    )
    app_log.info("Startup complete")

    yield

    app_log.info("Shutting down...")
    await close_db()
    app_log.info("Shutdown complete")


app = FastAPI(
    title="Bid Info Extractor",
    description="标书信息提取与应答系统 — 导入招标文件，自动提取关键信息、生成应答文件、同步飞书日历",
    version="2.0.0",
    lifespan=lifespan,
)


# ── Global exception handler ─────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions, log them, and return a clean JSON error."""
    tb = traceback.format_exc()
    log_error(
        "global",
        str(exc),
        {"method": request.method, "path": str(request.url.path), "traceback": tb[:500]},
    )
    return JSONResponse(
        status_code=500,
        content={"detail": f"服务器内部错误: {str(exc)}"},
    )


# ── Request logging middleware ───────────────────────────

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, and status."""
    response = await call_next(request)
    log_request(request.method, str(request.url.path), response.status_code)
    return response


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

# External API (with Bearer token auth)
try:
    from app.routers.external import router as external_router

    app.include_router(external_router)
except ImportError:
    app_log.warning("External API router not loaded")
