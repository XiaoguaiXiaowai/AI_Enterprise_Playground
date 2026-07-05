from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class McpServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)

    name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    transport: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    server_type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    config_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class McpToolCall(Base):
    __tablename__ = "mcp_tool_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    server_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("mcp_servers.id", ondelete="SET NULL"), index=True, nullable=True)

    request_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False, default="ok")

    input_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    output_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

