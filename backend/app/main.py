from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import get_settings
from app.core.middleware import AuthAndAuditMiddleware

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "NeuroSleep Twin API — research-prototype platform for event-level "
        "neuro-respiratory phenotyping. Not a diagnostic device."
    ),
)

# Order matters: added first = innermost, so CORS (added second) wraps
# around auth and handles preflight OPTIONS before auth ever sees it.
app.add_middleware(AuthAndAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict:
    return {"service": settings.app_name, "docs": "/docs"}
