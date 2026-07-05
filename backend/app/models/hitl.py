from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class HitlRequest(Base):
    __tablename__ = "hitl_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    server_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mcp_servers.id", ondelete="SET NULL"), index=True, nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False, default="pending")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    decided_by_user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_status: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    execution_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    tool_call_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mcp_tool_calls.id", ondelete="SET NULL"), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

