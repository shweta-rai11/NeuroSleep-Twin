from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session as DbSession

from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.apple_health import ScanResultOut, SleepSessionOut
from app.schemas.study import StudyOut
from app.services.ingestion.apple_health import (
    DATASET_ID,
    AppleHealthImportError,
    import_night,
    save_export,
    scan_sleep_sessions,
)

router = APIRouter(tags=["apple-health"])


@router.post("/apple-health/scan", response_model=ScanResultOut)
async def scan_apple_health_export(file: UploadFile = File(...)) -> ScanResultOut:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")
    content = await file.read()
    try:
        source_id = save_export(file.filename, content)
        result = scan_sleep_sessions(source_id)
    except AppleHealthImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not result.sessions:
        raise HTTPException(status_code=400, detail="No sleep-stage records found in this export.")

    return ScanResultOut(
        source_id=result.source_id,
        sessions=[
            SleepSessionOut(index=s.index, start=s.start.isoformat(), end=s.end.isoformat(),
                             duration_hours=round(s.duration_hours, 2), record_count=s.record_count)
            for s in result.sessions
        ],
    )


@router.post("/apple-health/{source_id}/import/{session_index}", response_model=StudyOut)
def import_apple_health_night(source_id: str, session_index: int, db: DbSession = Depends(get_db)) -> Study:
    result = scan_sleep_sessions(source_id)
    session = next((s for s in result.sessions if s.index == session_index), None)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_index} not found for this export.")

    record_name = f"{source_id}-{session_index}"
    existing = (
        db.query(Study).filter(Study.dataset_id == DATASET_ID, Study.record_name == record_name).one_or_none()
    )
    if existing is not None:
        return existing

    study = Study(
        dataset_id=DATASET_ID, record_name=record_name, source="upload",
        display_name=f"Apple Health — night of {session.start.date().isoformat()}",
        status="downloading",
    )
    db.add(study)
    db.commit()
    db.refresh(study)

    try:
        import_night(db, study, source_id, session.start, session.end)
        study.status = "ingested"
        db.commit()
        db.refresh(study)
        return study
    except Exception as exc:  # noqa: BLE001 — persisted for API/UI visibility, then re-raised
        db.rollback()
        study.status = "error"
        study.error_message = str(exc)[:1024]
        db.commit()
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc
