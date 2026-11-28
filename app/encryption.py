"""Authenticated Encryption Utility for OAuth Tokens and Sensitive Verifiers.

Uses authenticated symmetric encryption (Fernet: AES-128-CBC with HMAC-SHA256 authentication).
Ensures sensitive tokens (access tokens, refresh tokens, PKCE verifiers) are never stored in plaintext.
"""
from __future__ import annotations

import base64
import hashlib
import logging
from typing import Union

from cryptography.fernet import Fernet, InvalidToken

from app import config

logger = logging.getLogger("secondhour.encryption")


class EncryptionError(Exception):
    """Raised when encryption or authenticated decryption fails."""
    pass


def _derive_fernet_key(raw_key: Union[str, bytes]) -> bytes:
    """Ensure raw key is a valid 32-byte urlsafe-base64-encoded key for Fernet."""
    if isinstance(raw_key, str):
        key_bytes = raw_key.strip().encode("utf-8")
    else:
        key_bytes = raw_key

    # If it's already a valid 44-character urlsafe-base64 Fernet key, test it
    if len(key_bytes) == 44:
        try:
            base64.urlsafe_b64decode(key_bytes)
            return key_bytes
        except Exception:
            pass

    # Otherwise deterministically derive 32 bytes via SHA-256 and base64-encode
    digest = hashlib.sha256(key_bytes).digest()
    return base64.urlsafe_b64encode(digest)


def get_fernet(key: Union[str, bytes, None] = None) -> Fernet:
    """Instantiate a Fernet authenticated cipher using the specified or configured key."""
    active_key = key or getattr(config, "TOKEN_ENCRYPTION_KEY", "")
    if not active_key:
        raise EncryptionError("TOKEN_ENCRYPTION_KEY is not configured.")
    try:
        fernet_key = _derive_fernet_key(active_key)
        return Fernet(fernet_key)
    except Exception as exc:
        raise EncryptionError(f"Failed to initialize encryption cipher: {exc}") from exc


def encrypt_token(plaintext: Union[str, bytes], key: Union[str, bytes, None] = None) -> str:
    """Encrypt a sensitive token or verifier using authenticated encryption.

    Returns:
        URL-safe ciphertext string with embedded HMAC authentication tag and timestamp.
    """
    if plaintext is None:
        return ""
    if isinstance(plaintext, str):
        data_bytes = plaintext.encode("utf-8")
    else:
        data_bytes = plaintext

    try:
        f = get_fernet(key)
        encrypted_bytes = f.encrypt(data_bytes)
        return encrypted_bytes.decode("utf-8")
    except Exception as exc:
        logger.error("Token encryption failed: %s", exc)
        raise EncryptionError("Failed to encrypt token.") from exc


def decrypt_token(ciphertext: Union[str, bytes], key: Union[str, bytes, None] = None) -> str:
    """Decrypt and authenticate a ciphertext token.

    Raises:
        EncryptionError: If the authentication tag is invalid (tampered data) or key is wrong.
    """
    if not ciphertext:
        return ""
    if isinstance(ciphertext, str):
        cipher_bytes = ciphertext.strip().encode("utf-8")
    else:
        cipher_bytes = ciphertext

    try:
        f = get_fernet(key)
        decrypted_bytes = f.decrypt(cipher_bytes)
        return decrypted_bytes.decode("utf-8")
    except InvalidToken as exc:
        logger.warning("Token decryption failed: invalid token, tampered data, or key mismatch.")
        raise EncryptionError("Invalid or corrupted token: authentication tag validation failed.") from exc
    except Exception as exc:
        logger.error("Token decryption unexpected failure: %s", exc)
        raise EncryptionError(f"Failed to decrypt token: {exc}") from exc


def generate_encryption_key() -> str:
    """Generate a fresh 32-byte base64-encoded key suitable for TOKEN_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode("ascii")
