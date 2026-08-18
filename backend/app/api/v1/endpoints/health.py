from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    """Liveness/readiness probe. Confirms the API is up and reports build info."""
    settings = get_settings()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "demo_mode": settings.demo_mode,
    }
