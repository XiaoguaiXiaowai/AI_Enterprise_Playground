from __future__ import annotations

import json
import time

import httpx


class StreamableHttpMcpTransport:
    def __init__(
        self,
        *,
        url: str,
        headers: dict[str, str] | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._url = url
        self._headers = headers or {}
        self._timeout = timeout_s
        self._next_id = 1
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "StreamableHttpMcpTransport":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    async def request(self, *, method: str, params: dict) -> dict:
        if not self._client:
            raise RuntimeError("mcp_transport_not_started")

        req_id = self._next_id
        self._next_id += 1
        message = {"jsonrpc": "2.0", "id": req_id, "method": method, "params": params}

        r = await self._client.post(self._url, json=message, headers=self._headers)
        ct = (r.headers.get("content-type") or "").lower()
        if ct.startswith("text/event-stream"):
            return await self._read_sse_response(response=r, request_id=req_id)
        data = r.json()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(json.dumps(data.get("error"), ensure_ascii=False))
        if isinstance(data, dict):
            if data.get("id") == req_id:
                return data.get("result") or {}
            return data.get("result") or {}
        return {}

    async def timed_request(self, *, method: str, params: dict) -> tuple[dict, int]:
        start = time.perf_counter()
        result = await self.request(method=method, params=params)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return result, duration_ms

    async def _read_sse_response(self, *, response: httpx.Response, request_id: int) -> dict:
        buf = ""
        async for chunk in response.aiter_text():
            buf += chunk
            while "\n\n" in buf:
                event, buf = buf.split("\n\n", 1)
                data_lines = []
                for line in event.splitlines():
                    if line.startswith("data:"):
                        data_lines.append(line[5:].strip())
                if not data_lines:
                    continue
                payload = "\n".join(data_lines)
                try:
                    msg = json.loads(payload)
                except Exception:
                    continue
                if not isinstance(msg, dict):
                    continue
                if msg.get("id") != request_id:
                    continue
                if "error" in msg:
                    raise RuntimeError(json.dumps(msg.get("error"), ensure_ascii=False))
                return msg.get("result") or {}
        raise RuntimeError("mcp_sse_no_response")

