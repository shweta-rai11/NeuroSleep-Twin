from app.db.session import SessionLocal
from app.services.ingestion.upload import ingest_upload
from app.worker.celery_app import celery_app


@celery_app.task(name="ingest_upload", bind=True)
def ingest_upload_task(self, study_id: int) -> dict:
    db = SessionLocal()
    try:
        study = ingest_upload(db, study_id)
        return {"study_id": study.id, "status": study.status}
    finally:
        db.close()
