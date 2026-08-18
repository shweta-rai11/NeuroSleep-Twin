import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.annotation import Annotation
    from app.db.models.channel import Channel
    from app.db.models.respiratory_event import RespiratoryEvent


class Study(Base):
    """A single ingested recording — a MIT-BIH PSG record (`source="public"`)
    or a user-uploaded study (`source="upload"`). `dataset_id` is the
    registry entry id (see data/datasets/registry/) for public data, or the
    constant "user-upload" for uploads; `record_name` is the PhysioNet
    record name or a generated upload id.
    """

    __tablename__ = "studies"
    __table_args__ = (UniqueConstraint("dataset_id", "record_name", name="uq_study_dataset_record"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(64), index=True)
    record_name: Mapped[str] = mapped_column(String(128))
    source: Mapped[str] = mapped_column(String(16), default="public")
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    channel_mapping_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    channels: Mapped[list["Channel"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    annotations: Mapped[list["Annotation"]] = relationship(back_populates="study", cascade="all, delete-orphan")
    respiratory_events: Mapped[list["RespiratoryEvent"]] = relationship(
        back_populates="study", cascade="all, delete-orphan"
    )
