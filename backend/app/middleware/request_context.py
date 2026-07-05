import contextvars
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
import structlog

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models.auth import User

request_id_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(self.header_name) or str(uuid4())
        token = request_id_ctx.set(request_id)
        structlog.contextvars.bind_contextvars(request_id=request_id)
        request.state.request_id = request_id
        request.state.user_id = None
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer "):
            token_str = auth.split(" ", 1)[1].strip()
            db = SessionLocal()
            try:
                payload = decode_token(token_str)
                if payload.get("type") == "access" and payload.get("sub"):
                    user = db.get(User, int(payload["sub"]))
                    if user and user.is_active:
                        request.state.user_id = user.id
                        structlog.contextvars.bind_contextvars(user_id=user.id)
            except Exception:
                pass
            finally:
                db.close()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
            request_id_ctx.reset(token)
        response.headers[self.header_name] = request_id
        return response
