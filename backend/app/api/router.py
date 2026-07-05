from fastapi import APIRouter, Depends, Request

from app.config.settings import Settings, get_settings
from app.core.rate_limit import limiter

router = APIRouter()


@router.get("/", tags=["system"])
def root(settings: Settings = Depends(get_settings)) -> dict:
    return {"name": settings.app_name, "environment": settings.environment}


@router.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@router.get("/version", tags=["system"])
def version(settings: Settings = Depends(get_settings)) -> dict:
    return {"version": settings.version}


@router.get("/rate-limited", tags=["system"])
@limiter.limit("2/minute")
def rate_limited(request: Request) -> dict:
    return {"status": "ok"}
