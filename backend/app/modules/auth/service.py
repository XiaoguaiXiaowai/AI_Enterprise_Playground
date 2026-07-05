from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    new_token_jti,
    verify_password,
)
from app.models.auth import RefreshToken, Role, User


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def get_or_create_default_role(db: Session) -> Role:
    role = db.scalar(select(Role).where(Role.name == "user"))
    if role:
        return role
    role = Role(name="user")
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def create_user_with_password(db: Session, *, email: str, password: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user:
        raise ValueError("email_exists")
    role = get_or_create_default_role(db)
    user = User(email=email, password_hash=hash_password(password), roles=[role])
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, email: str, password: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.password_hash:
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def issue_tokens(db: Session, *, user: User) -> tuple[str, str]:
    access_token, _ = create_access_token(sub=str(user.id))
    jti = new_token_jti()
    refresh_token, refresh_expires_at = create_refresh_token(sub=str(user.id), jti=jti)
    db.add(RefreshToken(user_id=user.id, jti=jti, expires_at=refresh_expires_at))
    db.commit()
    return access_token, refresh_token


def rotate_refresh_token(db: Session, *, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise ValueError("invalid_refresh_token")

    sub = payload.get("sub")
    jti = payload.get("jti")
    if not sub or not jti:
        raise ValueError("invalid_refresh_token")

    stored = db.scalar(select(RefreshToken).where(RefreshToken.jti == jti))
    if not stored or stored.revoked_at is not None:
        raise ValueError("invalid_refresh_token")
    if _to_utc_aware(stored.expires_at) <= _now():
        raise ValueError("expired_refresh_token")

    stored.revoked_at = _now()
    db.add(stored)

    user = db.get(User, int(sub))
    if not user or not user.is_active:
        raise ValueError("invalid_refresh_token")

    access_token, _ = create_access_token(sub=str(user.id))
    new_jti = new_token_jti()
    new_refresh_token, new_refresh_expires_at = create_refresh_token(sub=str(user.id), jti=new_jti)
    db.add(RefreshToken(user_id=user.id, jti=new_jti, expires_at=new_refresh_expires_at))
    db.commit()

    return access_token, new_refresh_token


def get_or_create_github_user(db: Session, *, github_id: str, github_login: str, email: str | None) -> User:
    user = db.scalar(select(User).where(User.github_id == github_id))
    if user:
        if email and user.email != email:
            user.email = email
        user.github_login = github_login
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    role = get_or_create_default_role(db)
    fallback_email = email or f"{github_login}@users.noreply.github.com"
    existing_email_user = db.scalar(select(User).where(User.email == fallback_email))
    if existing_email_user:
        existing_email_user.github_id = github_id
        existing_email_user.github_login = github_login
        db.add(existing_email_user)
        db.commit()
        db.refresh(existing_email_user)
        return existing_email_user

    user = User(email=fallback_email, password_hash=None, github_id=github_id, github_login=github_login, roles=[role])
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
