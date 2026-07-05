from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.router import router as system_router
from app.api.v1.router import create_v1_router
from app.config.settings import get_settings
from app.core.errors import (
    http_exception_handler,
    rate_limit_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging import configure_logging
from app.core.oauth import create_oauth
from app.core.rate_limit import limiter
from app.middleware.request_context import RequestContextMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.modules.auth.router import router as auth_router
from app.modules.agents.router import router as agents_router
from app.modules.chat.router import router as chat_router
from app.modules.context.router import router as context_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.guardrails.router import router as guardrails_router
from app.modules.hitl.router import router as hitl_router
from app.modules.memory.router import router as memory_router
from app.modules.mcp.router import router as mcp_router
from app.modules.rag.router import router as rag_router
from app.modules.realtime.router import router as realtime_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    app = FastAPI(title=settings.app_name, version=settings.version)

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_middleware(SessionMiddleware, secret_key=settings.session_secret_key)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    app.state.oauth = create_oauth()

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    app.include_router(create_v1_router(settings.api_version))
    app.include_router(system_router)
    app.include_router(auth_router)
    app.include_router(agents_router)
    app.include_router(chat_router)
    app.include_router(context_router)
    app.include_router(dashboard_router)
    app.include_router(guardrails_router)
    app.include_router(hitl_router)
    app.include_router(memory_router)
    app.include_router(mcp_router)
    app.include_router(rag_router)
    app.include_router(realtime_router)
    return app


app = create_app()
