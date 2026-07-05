from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from app.modules.realtime.protocol import RealtimeEvent


async def demo_stream(input_text: str) -> AsyncGenerator[dict, None]:
    yield {"event": RealtimeEvent.thinking, "data": {"message": "thinking"}}
    await asyncio.sleep(0.05)

    yield {"event": RealtimeEvent.searching, "data": {"message": "searching"}}
    await asyncio.sleep(0.05)

    acc = ""
    for part in input_text.split():
        delta = part + " "
        acc += delta
        yield {"event": RealtimeEvent.token, "data": {"delta": delta}}
        await asyncio.sleep(0.01)

    yield {"event": RealtimeEvent.completed, "data": {"text": acc.rstrip()}}

