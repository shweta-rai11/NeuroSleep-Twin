from app.db.session import SessionLocal
from app.services.ingestion.mitbih import ingest_record
from app.worker.celery_app import celery_app


@celery_app.task(name="ingest_mitbih_record", bind=True)
def ingest_mitbih_record_task(self, record_name: str) -> dict:
    db = SessionLocal()
    try:
        study = ingest_record(db, record_name)
        return {"study_id": study.id, "status": study.status}
    finally:
        db.close()
