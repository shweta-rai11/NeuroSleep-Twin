from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.study import Study


class Annotation(Base):
    """A source annotation carried over verbatim from the original dataset
    (e.g. MIT-BIH PSG's per-epoch sleep-stage/apnea codes). Kept as raw,
    unmodified provenance — event detection (Phase 7+) derives its own
    structured event tables rather than overwriting these.
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), index=True)
    onset_sec: Mapped[float] = mapped_column(Float)
    duration_sec: Mapped[float] = mapped_column(Float)
    label: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(32))

    study: Mapped["Study"] = relationship(back_populates="annotations")
