"""AES-256-GCM encryption for sensitive configuration values.

Key derivation via PBKDF2-SHA256 (600,000 iterations, OWASP 2023 minimum).
Stores ciphertext as a single compact base64 token: nonce(12) + ciphertext + tag(16).
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def derive_key(master_password: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    """Derive a 256-bit AES key from a master password using PBKDF2-SHA256.

    Returns (key, salt). The salt must be stored alongside ciphertext so the
    key can be re-derived at decryption time.
    """
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=600_000,
    )
    key = kdf.derive(master_password.encode("utf-8"))
    return key, salt


def encrypt(key: bytes, plaintext: str) -> str:
    """Encrypt *plaintext* under *key* with AES-256-GCM.

    Returns a single base64-encoded token containing nonce + ciphertext + tag.
    Store this token in the database.
    """
    nonce = os.urandom(12)  # 96-bit nonce
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce))
    encryptor = cipher.encryptor()
    ct = encryptor.update(plaintext.encode("utf-8")) + encryptor.finalize()
    # Pack: nonce(12) + ciphertext + tag(16)
    token = base64.b64encode(nonce + ct + encryptor.tag).decode()
    return token


def decrypt(key: bytes, token: str) -> str:
    """Decrypt a token previously produced by *encrypt*.

    Raises InvalidTag if the ciphertext was tampered with or the wrong key
    was supplied.
    """
    raw = base64.b64decode(token)
    nonce, ct, tag = raw[:12], raw[12:-16], raw[-16:]
    cipher = Cipher(algorithms.AES(key), modes.GCM(nonce, tag))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ct) + decryptor.finalize()
    return plaintext.decode("utf-8")


# ── High-level helpers for settings integration ──────────


def encrypt_value(plaintext: str, master_password: str) -> str:
    """Encrypt a single value with key derived from master_password.

    The returned token is self-contained (includes salt in a prefix).
    Format: base64(salt) + ":" + base64(nonce+ct+tag)
    """
    key, salt = derive_key(master_password)
    token = encrypt(key, plaintext)
    salt_b64 = base64.b64encode(salt).decode()
    return f"{salt_b64}:{token}"


def decrypt_value(encrypted: str, master_password: str) -> str:
    """Decrypt a value produced by encrypt_value."""
    salt_b64, token = encrypted.split(":", 1)
    salt = base64.b64decode(salt_b64)
    key, _ = derive_key(master_password, salt)
    return decrypt(key, token)


def is_encrypted(value: str | None) -> bool:
    """Heuristic: check if a value looks like an encrypted token."""
    if not value:
        return False
    # Encrypted tokens have salt:token format, both base64
    parts = value.split(":", 1)
    if len(parts) != 2:
        return False
    try:
        base64.b64decode(parts[0])
        base64.b64decode(parts[1])
        return True
    except Exception:
        return False
