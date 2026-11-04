from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from config import settings

TOKEN_TTL_SECONDS = 7 * 24 * 3600


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":", 1)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), 120_000)
    return hmac.compare_digest(digest.hex(), digest_hex)


def password_is_strong(password: str) -> bool:
    if not 8 <= len(password) <= 128:
        return False
    return any(character.isalpha() for character in password) and any(character.isdigit() for character in password)


def issue_token(user_id: str, session_version: int = 0) -> str:
    payload = {
        "sub": user_id,
        "ver": session_version,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    raw = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signature = hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def read_token(token: str) -> tuple[str, int] | None:
    if "." not in token:
        return None
    raw, signature = token.rsplit(".", 1)
    expected = hmac.new(settings.secret_key.encode(), raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        return None
    padded = raw + "=" * (-len(raw) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except (json.JSONDecodeError, ValueError):
        return None
    if int(payload.get("exp", 0)) < time.time():
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None
    version = payload.get("ver", 0)
    return subject, version if isinstance(version, int) else 0
