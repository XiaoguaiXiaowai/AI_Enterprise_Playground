import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

from app.core.database import SessionLocal
from app.modules.context.service import log_event

log = structlog.get_logger("request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = None
        try:
            response = await call_next(request)
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            client = request.client.host if request.client else None
            log.info(
                "request",
                method=request.method,
                path=str(request.url.path),
                status_code=getattr(response, "status_code", None),
                duration_ms=round(duration_ms, 2),
                client=client,
            )
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                user_id = getattr(request.state, "user_id", None)
                db = SessionLocal()
                try:
                    log_event(
                        db,
                        request_id=str(request_id),
                        user_id=int(user_id) if isinstance(user_id, int) else None,
                        event_type="http_request",
                        data={
                            "method": request.method,
                            "path": str(request.url.path),
                            "status_code": getattr(response, "status_code", None),
                            "duration_ms": round(duration_ms, 2),
                        },
                    )
                finally:
                    db.close()
        return response
