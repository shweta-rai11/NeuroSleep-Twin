"""Importing this package registers every model on Base.metadata — required
before Alembic autogenerate or Base.metadata.create_all() can see them."""

from app.db.base import Base
from app.db.models.annotation import Annotation
from app.db.models.audit_log import AuditLog
from app.db.models.channel import Channel
from app.db.models.phenotype_label import PhenotypeLabel
from app.db.models.respiratory_event import RespiratoryEvent
from app.db.models.study import Study

__all__ = ["Base", "Study", "Channel", "Annotation", "RespiratoryEvent", "PhenotypeLabel", "AuditLog"]
