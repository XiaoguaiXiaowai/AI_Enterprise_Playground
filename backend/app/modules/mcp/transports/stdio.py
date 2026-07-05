from __future__ import annotations

import asyncio
import json
import os
import time


class StdioMcpTransport:
    def __init__(self, *, command: list[str], env: dict[str, str] | None = None, cwd: str | None = None) -> None:
        self._command = command
        self._env = env
        self._cwd = cwd

        self._proc: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._pending: dict[int, asyncio.Future[dict]] = {}
        self._next_id = 1

    async def __aenter__(self) -> "StdioMcpTransport":
        merged_env = os.environ.copy()
        if self._env:
            merged_env.update({k: str(v) for k, v in self._env.items()})

        self._proc = await asyncio.create_subprocess_exec(
            *self._command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self._cwd,
            env=merged_env,
        )
        self._reader_task = asyncio.create_task(self._reader_loop())
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
            self._reader_task = None
        if self._proc:
            try:
                if self._proc.stdin:
                    self._proc.stdin.close()
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=1.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            self._proc = None

        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(RuntimeError("mcp_transport_closed"))
        self._pending.clear()

    async def request(self, *, method: str, params: dict) -> dict:
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("mcp_transport_not_started")

        req_id = self._next_id
        self._next_id += 1

        message = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}
        line = json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"
        fut: asyncio.Future[dict] = asyncio.get_running_loop().create_future()
        self._pending[req_id] = fut

        self._proc.stdin.write(line.encode("utf-8"))
        await self._proc.stdin.drain()
        return await fut

    async def timed_request(self, *, method: str, params: dict) -> tuple[dict, int]:
        start = time.perf_counter()
        result = await self.request(method=method, params=params)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return result, duration_ms

    async def _reader_loop(self) -> None:
        assert self._proc and self._proc.stdout
        reader = self._proc.stdout
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                msg = json.loads(line.decode("utf-8").strip())
            except Exception:
                continue
            if not isinstance(msg, dict):
                continue
            msg_id = msg.get("id")
            if not isinstance(msg_id, int):
                continue
            fut = self._pending.pop(msg_id, None)
            if not fut or fut.done():
                continue
            if "error" in msg:
                fut.set_exception(RuntimeError(json.dumps(msg.get("error"), ensure_ascii=False)))
                continue
            fut.set_result(msg.get("result") or {})
