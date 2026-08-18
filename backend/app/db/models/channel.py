from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.study import Study


class Channel(Base):
    """One recorded channel of a study. `signal_type` is the standardized
    type (e.g. "eeg", "ecg", "resp", "spo2") — set from an editable
    best-effort guess at ingestion time (see app/services/channel_mapping.py)
    with a `mapping_confidence`; `mapping_confirmed` only becomes true once
    a person has reviewed/corrected it on the Channel Mapping screen
    (Phase 4) — later pipeline stages should not trust an unconfirmed
    mapping. `storage_key` points at the raw float32 waveform in object
    storage.
    """

    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    signal_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    mapping_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    mapping_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sampling_rate: Mapped[float] = mapped_column(Float)
    n_samples: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String(512))

    study: Mapped["Study"] = relationship(back_populates="channels")
