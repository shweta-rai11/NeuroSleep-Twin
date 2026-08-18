import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.assistant import AskRequest, AskResponse
from app.services.explainability.assistant import answer_question
from app.services.explainability.context import build_study_context

router = APIRouter(tags=["assistant"])


@router.get("/assistant/status")
def get_assistant_status() -> dict:
    settings = get_settings()

    if settings.ollama_model:
        try:
            httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0).raise_for_status()
            return {"configured": True, "provider": "ollama", "model": settings.ollama_model}
        except Exception:  # noqa: BLE001 — server not reachable, fall through
            pass

    if settings.anthropic_api_key:
        return {"configured": True, "provider": "anthropic", "model": settings.anthropic_model}

    return {"configured": False, "provider": None, "model": None}


@router.post("/studies/{study_id}/assistant/ask", response_model=AskResponse)
def ask_assistant(study_id: int, body: AskRequest, db: Session = Depends(get_db)) -> AskResponse:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")

    context = build_study_context(db, study)
    result = answer_question(context, body.question)
    return AskResponse(answer=result.answer, configured=result.configured, evidence=result.evidence)
