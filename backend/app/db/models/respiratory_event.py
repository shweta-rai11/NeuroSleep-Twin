from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.study import Study


class RespiratoryEvent(Base):
    """A candidate respiratory event (apnea/hypopnea) detected from a
    respiratory-effort/airflow channel — a "Machine-learning estimate" per
    the README's labeling scheme, never a clinical scoring. One row per
    event accumulates feature columns as later pipeline phases run against
    it: oxygen (Phase 7), cortical/EEG response (Phase 9), autonomic
    response (Phase 10) — the event fingerprint (Phase 11) is just these
    columns normalized into a vector, not a separately stored thing.
    """

    __tablename__ = "respiratory_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_id: Mapped[int] = mapped_column(ForeignKey("studies.id"), index=True)
    channel_id: Mapped[int] = mapped_column(ForeignKey("channels.id", ondelete="CASCADE"))
    algorithm_version: Mapped[str] = mapped_column(String(32))

    onset_sec: Mapped[float] = mapped_column(Float)
    duration_sec: Mapped[float] = mapped_column(Float)
    event_type: Mapped[str] = mapped_column(String(16))  # "apnea" | "hypopnea"
    depth_ratio: Mapped[float] = mapped_column(Float)  # min envelope / local baseline during the event

    # Oxygen burden (Phase 7) — populated only when the study has an SpO2 channel.
    spo2_baseline: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2_nadir: Mapped[float | None] = mapped_column(Float, nullable=True)
    desaturation_depth: Mapped[float | None] = mapped_column(Float, nullable=True)
    desaturation_slope: Mapped[float | None] = mapped_column(Float, nullable=True)  # %/sec, fall to nadir
    recovery_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Cortical/EEG response (Phase 9) — relative band power in the peri-event window.
    eeg_delta_rel: Mapped[float | None] = mapped_column(Float, nullable=True)
    eeg_theta_rel: Mapped[float | None] = mapped_column(Float, nullable=True)
    eeg_alpha_rel: Mapped[float | None] = mapped_column(Float, nullable=True)
    eeg_beta_rel: Mapped[float | None] = mapped_column(Float, nullable=True)
    arousal_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Autonomic response (Phase 10) — from an ECG-derived instantaneous HR series.
    hr_baseline_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_peak_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hr_response_bpm: Mapped[float | None] = mapped_column(Float, nullable=True)

    study: Mapped["Study"] = relationship(back_populates="respiratory_events")
