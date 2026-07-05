#!/usr/bin/env python3
"""One-time migration: encrypt plaintext secrets in the database.

Run this ONCE after setting ENCRYPTION_MASTER_PASSWORD in .env.
Existing encrypted values will be skipped.
"""

import asyncio
import os
import sys

# Ensure we can import from the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env first (before importing app modules)
from pathlib import Path
_env_file = Path(__file__).resolve().parent.parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _key, _, _val = _line.partition("=")
                _key = _key.strip()
                _val = _val.strip().strip('"').strip("'")
                if _key not in os.environ:
                    os.environ[_key] = _val

from sqlalchemy import select
from app.db.database import async_session
from app.db.models import AppConfig
from app.config import SENSITIVE_KEYS, settings


async def main():
    if not settings.encryption_master_password:
        print("ERROR: ENCRYPTION_MASTER_PASSWORD not set in .env")
        print("Create a .env file with: ENCRYPTION_MASTER_PASSWORD=<random-40-chars>")
        sys.exit(1)

    enc_key = settings._get_encryption_key()
    if not enc_key:
        print("ERROR: Failed to derive encryption key")
        sys.exit(1)

    async with async_session() as db:
        result = await db.execute(select(AppConfig))
        rows = result.scalars().all()

        encrypted_count = 0
        skipped_count = 0

        for row in rows:
            if row.encrypted:
                skipped_count += 1
                continue
            if row.key not in SENSITIVE_KEYS:
                continue
            if not row.value:
                continue

            # Encrypt the value
            from app.security.crypto import encrypt
            token = encrypt(enc_key, row.value)

            row.value = token
            row.encrypted = 1
            encrypted_count += 1
            print(f"  Encrypted: {row.key}")

        await db.commit()
        print(f"\nDone: {encrypted_count} encrypted, {skipped_count} already encrypted, {len(rows)} total rows")


if __name__ == "__main__":
    asyncio.run(main())
