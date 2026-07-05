"""Configuration management API routes — with AES-256-GCM encryption for secrets."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import SENSITIVE_KEYS, settings
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


@router.get("")
async def get_config():
    """Get current configuration. Secrets are returned as plaintext for the settings page."""
    return settings.to_dict_with_secrets()


@router.put("")
async def update_config(
    data: ConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update configuration. Sensitive values are encrypted before storage."""
    overrides: dict[str, str] = {}
    encrypted_keys: set[str] = set()

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
        if not value:
            continue

        # Encrypt sensitive values before storing
        stored_value, was_encrypted = settings.encrypt_if_sensitive(key, value)

        # Upsert into DB
        existing = await db.get(AppConfig, key)
        if existing:
            existing.value = stored_value
            existing.encrypted = 1 if was_encrypted else 0
        else:
            db.add(AppConfig(key=key, value=stored_value, encrypted=1 if was_encrypted else 0))

        if was_encrypted:
            encrypted_keys.add(key)

        # Pass plaintext to runtime overrides
        overrides[key] = value

    await db.flush()

    # Apply to runtime
    settings.apply_overrides(overrides)
    settings.mark_encrypted_keys(encrypted_keys)

    return {
        "message": "配置已保存",
        "updated": list(overrides.keys()),
        "encrypted_fields": list(encrypted_keys),
        "encryption_enabled": bool(settings._get_encryption_key()),
    }


@router.post("/test-llm")
async def test_llm_connection(data: ConfigUpdate):
    """Test LLM API connection with provided credentials."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=data.llm_api_key or settings.llm_api_key,
        base_url=data.llm_base_url or settings.llm_base_url,
    )

    try:
        response = await client.chat.completions.create(
            model=data.llm_model or settings.llm_model,
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


@router.post("/generate-token")
async def generate_api_token(db: AsyncSession = Depends(get_db)):
    """Generate a new API Bearer Token for external API access."""
    from app.security.auth import generate_api_token

    token = generate_api_token()

    # Encrypt before storing
    stored_value, was_encrypted = settings.encrypt_if_sensitive("api_auth_token", token)

    existing = await db.get(AppConfig, "api_auth_token")
    if existing:
        existing.value = stored_value
        existing.encrypted = 1 if was_encrypted else 0
    else:
        db.add(AppConfig(key="api_auth_token", value=stored_value, encrypted=1 if was_encrypted else 0))

    await db.flush()

    # Apply to runtime
    settings.apply_overrides({"api_auth_token": token})

    return {
        "token": token,
        "message": "Token 已生成，请妥善保存。此 Token 仅在本次显示。",
        "encrypted": was_encrypted,
    }


async def load_config_from_db(db: AsyncSession) -> dict[str, str]:
    """Load persisted config from DB on startup, decrypting sensitive values."""
    result = await db.execute(select(AppConfig))
    rows = result.scalars().all()

    overrides: dict[str, str] = {}
    encrypted_keys: set[str] = set()

    for row in rows:
        value = row.value or ""
        if row.encrypted:
            encrypted_keys.add(row.key)
            value = settings.decrypt_if_encrypted(row.key, value)
        overrides[row.key] = value

    settings.mark_encrypted_keys(encrypted_keys)
    return overrides
