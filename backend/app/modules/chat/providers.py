from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator


class ChatProvider:
    name: str

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        raise NotImplementedError


class MockEchoProvider(ChatProvider):
    name = "mock"

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        for ch in f"Echo: {prompt}":
            yield ch
            await asyncio.sleep(0.001)


class MockReverseProvider(ChatProvider):
    name = "mock-reverse"

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        for ch in f"Reverse: {prompt[::-1]}":
            yield ch
            await asyncio.sleep(0.001)


class MockToxicProvider(ChatProvider):
    name = "mock-toxic"

    async def stream(self, prompt: str) -> AsyncGenerator[str, None]:
        for ch in "I hate you":
            yield ch
            await asyncio.sleep(0.001)



def get_provider(model: str) -> ChatProvider:
    if model == MockReverseProvider.name:
        return MockReverseProvider()
    if model == MockToxicProvider.name:
        return MockToxicProvider()
    return MockEchoProvider()
