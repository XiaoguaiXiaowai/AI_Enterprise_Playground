import base64
import os
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.config.settings import get_settings


def hash_password(password: str) -> str:
    pw = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def _now() -> datetime:
    return datetime.now(UTC)


def new_token_jti() -> str:
    raw = os.urandom(16)
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def create_access_token(*, sub: str, expires_minutes: int | None = None, extra: dict | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    exp_minutes = expires_minutes if expires_minutes is not None else settings.access_token_expires_minutes
    expires_at = _now() + timedelta(minutes=exp_minutes)
    payload = {"sub": sub, "type": "access", "exp": expires_at}
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def create_refresh_token(*, sub: str, jti: str, expires_days: int | None = None) -> tuple[str, datetime]:
    settings = get_settings()
    exp_days = expires_days if expires_days is not None else settings.refresh_token_expires_days
    expires_at = _now() + timedelta(days=exp_days)
    payload = {"sub": sub, "type": "refresh", "jti": jti, "exp": expires_at}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

