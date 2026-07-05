from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from starlette.responses import JSONResponse


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    payload = {"detail": exc.detail, "request_id": _request_id(request)}
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    payload = {"detail": "validation_error", "errors": exc.errors(), "request_id": _request_id(request)}
    return JSONResponse(status_code=422, content=payload)


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    payload = {"detail": "rate_limited", "request_id": _request_id(request)}
    return JSONResponse(status_code=429, content=payload)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    payload = {"detail": "internal_server_error", "request_id": _request_id(request)}
    return JSONResponse(status_code=500, content=payload)

