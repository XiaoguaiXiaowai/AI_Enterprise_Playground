from __future__ import annotations

from enum import Enum
from uuid import uuid4


class RealtimeEvent(str, Enum):
    connected = "connected"
    thinking = "thinking"
    searching = "searching"
    token = "token"
    completed = "completed"
    failed = "failed"


def new_connection_id() -> str:
    return str(uuid4())

