from __future__ import annotations

"""Configuration management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db
from app.db.models import AppConfig

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    techtoexcel_path: str = ""
    techtoexcel_args: str = ""


class TestLLMRequest(BaseModel):
    base_url: str
    api_key: str
    model: str = "gpt-4o-mini"


@router.get("")
async def get_config():
    """Get current configuration (with masked secrets)."""
    return settings.to_dict_with_secrets()


@router.put("")
async def update_config(
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update configuration. Persists to SQLite and applies to runtime."""
    overrides = {}

    fields = [
        ("llm_base_url", data.llm_base_url),
        ("llm_api_key", data.llm_api_key),
        ("llm_model", data.llm_model),
        ("feishu_app_id", data.feishu_app_id),
        ("feishu_app_secret", data.feishu_app_secret),
        ("techtoexcel_path", data.techtoexcel_path),
        ("techtoexcel_args", data.techtoexcel_args),
    ]

    for key, value in fields:
        if value:  # Only store non-empty values
            # Upsert
            existing = await db.get(AppConfig, key)
            if existing:
                existing.value = value
            else:
                db.add(AppConfig(key=key, value=value))
            overrides[key] = value

    await db.flush()

    # Apply to runtime
    settings.apply_overrides(overrides)

    return {"message": "配置已保存", "updated": list(overrides.keys())}


@router.post("/test-llm")
async def test_llm_connection(req: TestLLMRequest):
    """Test LLM API connection with a simple chat completion."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=req.api_key, base_url=req.base_url)

    try:
        response = await client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        return {
            "success": True,
            "model": response.model,
            "response": response.choices[0].message.content,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def load_config_from_db(db: AsyncSession) -> dict[str, str]:
    """Load persisted config from DB on startup."""
    result = await db.execute(select(AppConfig))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows if row.value}
