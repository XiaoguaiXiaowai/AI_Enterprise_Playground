from fastapi import APIRouter

from app.api.router import router as system_router
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


def create_v1_router(version: str) -> APIRouter:
    router = APIRouter(prefix=f"/api/{version}")
    router.include_router(system_router)
    router.include_router(auth_router)
    router.include_router(agents_router)
    router.include_router(chat_router)
    router.include_router(context_router)
    router.include_router(dashboard_router)
    router.include_router(guardrails_router)
    router.include_router(hitl_router)
    router.include_router(memory_router)
    router.include_router(mcp_router)
    router.include_router(rag_router)
    router.include_router(realtime_router)
    return router
