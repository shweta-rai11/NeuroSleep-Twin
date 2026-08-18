import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.study import IngestJobOut
from app.services.ingestion.upload import (
    DATASET_ID,
    UnsupportedUploadError,
    save_uploaded_files,
    validate_file_signature,
    validate_filenames,
)
from app.worker.tasks.uploads import ingest_upload_task

router = APIRouter(tags=["uploads"])


@router.post("/uploads", response_model=IngestJobOut)
async def upload_study(
    files: list[UploadFile] = File(...),
    display_name: str | None = Form(None),
    db: Session = Depends(get_db),
) -> IngestJobOut:
    filenames = [f.filename for f in files if f.filename]
    if not filenames:
        raise HTTPException(status_code=400, detail="No files provided.")

    try:
        validate_filenames(filenames)
    except UnsupportedUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    upload_id = uuid.uuid4().hex
    contents = [(f.filename, await f.read()) for f in files if f.filename]
    try:
        for filename, content in contents:
            validate_file_signature(filename, content)
        save_uploaded_files(upload_id, contents)
    except UnsupportedUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    study = Study(
        dataset_id=DATASET_ID,
        record_name=upload_id,
        source="upload",
        display_name=display_name or filenames[0],
        status="pending",
    )
    db.add(study)
    db.commit()
    db.refresh(study)

    task = ingest_upload_task.delay(study.id)
    return IngestJobOut(task_id=task.id, status="queued")
