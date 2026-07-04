from __future__ import annotations

"""Application configuration management.

Loads settings from environment variables with fallback defaults.
Runtime overrides are stored in SQLite app_config table.
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"


class Settings:
    """Application settings with env-var fallback + DB override support."""

    def __init__(self):
        self._overrides: dict[str, str] = {}

    # -- LLM --
    @property
    def llm_base_url(self) -> str:
        return self._overrides.get("llm_base_url") or os.getenv(
            "LLM_BASE_URL", "https://api.openai.com/v1"
        )

    @property
    def llm_api_key(self) -> str:
        return self._overrides.get("llm_api_key") or os.getenv("LLM_API_KEY", "")

    @property
    def llm_model(self) -> str:
        return self._overrides.get("llm_model") or os.getenv("LLM_MODEL", "gpt-4o-mini")

    # -- Feishu --
    @property
    def feishu_app_id(self) -> str:
        return self._overrides.get("feishu_app_id") or os.getenv("FEISHU_APP_ID", "")

    @property
    def feishu_app_secret(self) -> str:
        return self._overrides.get("feishu_app_secret") or os.getenv("FEISHU_APP_SECRET", "")

    # -- Tech to Excel --
    @property
    def techtoexcel_path(self) -> str:
        return self._overrides.get("techtoexcel_path") or os.getenv("TECHTOEXCEL_PATH", "")

    @property
    def techtoexcel_args(self) -> str:
        return self._overrides.get("techtoexcel_args") or os.getenv("TECHTOEXCEL_ARGS", "")

    # -- System --
    @property
    def upload_dir(self) -> str:
        path = os.getenv("UPLOAD_DIR", str(UPLOAD_DIR))
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    @property
    def export_dir(self) -> str:
        path = os.getenv("EXPORT_DIR", str(EXPORT_DIR))
        Path(path).mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_url(self) -> str:
        return os.getenv(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{DATA_DIR}/bid_info_extractor.db",
        )

    @property
    def max_upload_size_mb(self) -> int:
        return int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))

    def apply_overrides(self, overrides: dict[str, str]) -> None:
        """Apply runtime configuration overrides from DB."""
        self._overrides.update(overrides)

    def to_dict(self) -> dict:
        """Export current settings as dict (excluding secrets)."""
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": "***" if self.llm_api_key else "",
            "llm_model": self.llm_model,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_secret": "***" if self.feishu_app_secret else "",
            "techtoexcel_path": self.techtoexcel_path,
            "techtoexcel_args": self.techtoexcel_args,
            "max_upload_size_mb": self.max_upload_size_mb,
        }

    def to_dict_with_secrets(self) -> dict:
        """Export with actual secret values (for API responses to settings page)."""
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": self.llm_api_key,
            "llm_model": self.llm_model,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_secret": self.feishu_app_secret,
            "techtoexcel_path": self.techtoexcel_path,
            "techtoexcel_args": self.techtoexcel_args,
            "max_upload_size_mb": self.max_upload_size_mb,
        }


# Global singleton
settings = Settings()
