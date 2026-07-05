"""Application configuration management.

Loads settings from environment variables with fallback defaults.
Runtime overrides are stored in SQLite app_config table.
Sensitive values are encrypted at rest via AES-256-GCM.
"""

from __future__ import annotations

import os
from pathlib import Path

# Auto-load .env file if present
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    with open(_ENV_FILE) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key not in os.environ:
                    os.environ[_key] = _val

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXPORT_DIR = DATA_DIR / "exports"

# Sensitive config keys that should be encrypted at rest
SENSITIVE_KEYS = {"llm_api_key", "feishu_app_secret", "api_auth_token"}


class Settings:
    """Application settings with env-var fallback + DB override support."""

    def __init__(self):
        self._overrides: dict[str, str] = {}
        self._encrypted: set[str] = set()
        self._encryption_key: bytes | None = None

    # ── Encryption ──────────────────────────────────────

    @property
    def encryption_master_password(self) -> str:
        return os.getenv("ENCRYPTION_MASTER_PASSWORD", "")

    def _get_encryption_key(self) -> bytes | None:
        """Lazily derive the AES key from master password."""
        if self._encryption_key is not None:
            return self._encryption_key
        pwd = self.encryption_master_password
        if not pwd:
            return None
        from app.security.crypto import derive_key

        # Use a fixed salt for the master key (not per-value)
        fixed_salt = b"bid-info-extractor-v2-master-salt"
        key, _ = derive_key(pwd, fixed_salt)
        self._encryption_key = key
        return key

    def encrypt_if_sensitive(self, key: str, value: str) -> tuple[str, bool]:
        """Encrypt a value if it's a sensitive key. Returns (value, was_encrypted)."""
        if key in SENSITIVE_KEYS and value:
            enc_key = self._get_encryption_key()
            if enc_key:
                from app.security.crypto import encrypt

                return encrypt(enc_key, value), True
        return value, False

    def decrypt_if_encrypted(self, key: str, value: str) -> str:
        """Decrypt a value if it's a sensitive key and appears encrypted."""
        if key in SENSITIVE_KEYS and value:
            enc_key = self._get_encryption_key()
            if enc_key:
                from app.security.crypto import decrypt, is_encrypted

                if is_encrypted(value):
                    try:
                        return decrypt(enc_key, value)
                    except Exception:
                        # If decryption fails, return as-is (might be plaintext from pre-encryption era)
                        pass
        return value

    # ── LLM (default: DeepSeek) ─────────────────────────

    @property
    def llm_base_url(self) -> str:
        return self._overrides.get("llm_base_url") or os.getenv(
            "LLM_BASE_URL", "https://api.deepseek.com/v1"
        )

    @property
    def llm_api_key(self) -> str:
        raw = self._overrides.get("llm_api_key") or os.getenv("LLM_API_KEY", "")
        return self.decrypt_if_encrypted("llm_api_key", raw) if raw else ""

    @property
    def llm_model(self) -> str:
        return self._overrides.get("llm_model") or os.getenv("LLM_MODEL", "deepseek-chat")

    # ── Feishu ──────────────────────────────────────────

    @property
    def feishu_app_id(self) -> str:
        return self._overrides.get("feishu_app_id") or os.getenv("FEISHU_APP_ID", "")

    @property
    def feishu_app_secret(self) -> str:
        raw = self._overrides.get("feishu_app_secret") or os.getenv("FEISHU_APP_SECRET", "")
        return self.decrypt_if_encrypted("feishu_app_secret", raw) if raw else ""

    # ── Tech to Excel ───────────────────────────────────

    @property
    def techtoexcel_path(self) -> str:
        return self._overrides.get("techtoexcel_path") or os.getenv("TECHTOEXCEL_PATH", "")

    @property
    def techtoexcel_args(self) -> str:
        return self._overrides.get("techtoexcel_args") or os.getenv("TECHTOEXCEL_ARGS", "")

    # ── API Auth ────────────────────────────────────────

    @property
    def api_auth_token(self) -> str:
        raw = self._overrides.get("api_auth_token") or os.getenv("API_AUTH_TOKEN", "")
        return self.decrypt_if_encrypted("api_auth_token", raw) if raw else ""

    # ── System ──────────────────────────────────────────

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

    # ── Override management ─────────────────────────────

    def apply_overrides(self, overrides: dict[str, str]) -> None:
        """Apply runtime configuration overrides from DB."""
        self._overrides.update(overrides)

    def mark_encrypted_keys(self, keys: set[str]) -> None:
        """Track which keys are stored encrypted."""
        self._encrypted = keys

    def to_dict(self) -> dict:
        """Export current settings (mask secrets for public display)."""
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": "***" if self.llm_api_key else "",
            "llm_model": self.llm_model,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_secret": "***" if self.feishu_app_secret else "",
            "techtoexcel_path": self.techtoexcel_path,
            "techtoexcel_args": self.techtoexcel_args,
            "api_auth_token": "***" if self.api_auth_token else "",
            "encryption_enabled": bool(self._get_encryption_key()),
            "max_upload_size_mb": self.max_upload_size_mb,
        }

    def to_dict_with_secrets(self) -> dict:
        """Export with actual secret values (for settings page)."""
        return {
            "llm_base_url": self.llm_base_url,
            "llm_api_key": self.llm_api_key,
            "llm_model": self.llm_model,
            "feishu_app_id": self.feishu_app_id,
            "feishu_app_secret": self.feishu_app_secret,
            "techtoexcel_path": self.techtoexcel_path,
            "techtoexcel_args": self.techtoexcel_args,
            "api_auth_token": self.api_auth_token,
            "encryption_enabled": bool(self._get_encryption_key()),
            "max_upload_size_mb": self.max_upload_size_mb,
        }


# Global singleton
settings = Settings()
