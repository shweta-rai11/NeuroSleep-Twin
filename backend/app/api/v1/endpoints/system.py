from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.audit_log import AuditLog
from app.db.session import get_db

router = APIRouter(tags=["system"])


@router.get("/audit-log")
def list_audit_log(limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(min(limit, 500)).all()
    return [
        {
            "id": r.id, "created_at": r.created_at.isoformat(), "method": r.method,
            "path": r.path, "status_code": r.status_code, "client_host": r.client_host,
        }
        for r in rows
    ]
