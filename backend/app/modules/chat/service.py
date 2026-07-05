from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import ChatMessage, ChatSession
from app.modules.chat.providers import get_provider


def create_session(db: Session, *, user_id: int, title: str) -> ChatSession:
    session = ChatSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(db: Session, *, user_id: int) -> list[ChatSession]:
    return list(db.scalars(select(ChatSession).where(ChatSession.user_id == user_id).order_by(ChatSession.id.desc())))


def get_session(db: Session, *, user_id: int, session_id: int) -> ChatSession | None:
    session = db.get(ChatSession, session_id)
    if not session or session.user_id != user_id:
        return None
    return session


def list_messages(db: Session, *, user_id: int, session_id: int) -> list[ChatMessage] | None:
    session = get_session(db, user_id=user_id, session_id=session_id)
    if not session:
        return None
    return list(
        db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.id.asc()))
    )


def add_message(db: Session, *, session_id: int, role: str, content: str, model: str) -> ChatMessage:
    msg = ChatMessage(session_id=session_id, role=role, content=content, model=model)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg


async def stream_assistant_reply(*, prompt: str, model: str) -> AsyncGenerator[str, None]:
    provider = get_provider(model)
    async for token in provider.stream(prompt):
        yield token


async def generate_assistant_text(*, prompt: str, model: str) -> str:
    text = ""
    async for t in stream_assistant_reply(prompt=prompt, model=model):
        text += t
    return text
