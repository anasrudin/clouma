"""AES-256-GCM encryption helpers for agent secrets.

Usage:
    from agent_runtime.crypto import encrypt_value, decrypt_value

    key = settings.secret_encryption_key
    ciphertext = encrypt_value("my-token", key)   # -> "base64..."
    plaintext  = decrypt_value(ciphertext, key)   # -> "my-token"

If SECRET_ENCRYPTION_KEY is not set (empty string), values are stored and
returned as-is (plaintext) for backward compatibility.

Key format: 64 hex characters = 32 bytes = 256-bit AES key.
Generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
"""

from __future__ import annotations

import base64
import os

_ENCRYPTED_PREFIX = "enc:"


def encrypt_value(plaintext: str, hex_key: str) -> str:
    """Encrypt a string with AES-256-GCM. Returns a base64-encoded blob.

    If hex_key is empty, returns plaintext unchanged.
    """
    if not hex_key:
        return plaintext

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = bytes.fromhex(hex_key)
    nonce = os.urandom(12)  # 96-bit nonce — unique per encryption
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode(), None)
    return _ENCRYPTED_PREFIX + base64.b64encode(nonce + ciphertext).decode()


def decrypt_value(stored: str, hex_key: str) -> str:
    """Decrypt a value produced by encrypt_value.

    If the value does not start with the encrypted prefix, returns it as-is
    (supports plaintext values written before encryption was enabled).
    """
    if not hex_key or not stored.startswith(_ENCRYPTED_PREFIX):
        return stored

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    key = bytes.fromhex(hex_key)
    raw = base64.b64decode(stored[len(_ENCRYPTED_PREFIX):])
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode()
