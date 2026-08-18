from pydantic import BaseModel, ConfigDict


class ChannelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    signal_type: str | None
    mapping_confidence: float
    mapping_confirmed: bool
    unit: str | None
    sampling_rate: float
    n_samples: int


class ChannelMappingUpdate(BaseModel):
    signal_type: str | None


class AnnotationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    onset_sec: float
    duration_sec: float
    label: str
    source: str


class StudyListItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: str
    record_name: str
    source: str
    display_name: str | None
    status: str
    channel_mapping_confirmed: bool
    duration_sec: float | None


class StudyOut(StudyListItemOut):
    error_message: str | None
    channels: list[ChannelOut]
    annotations: list[AnnotationOut]


class IngestJobOut(BaseModel):
    task_id: str
    status: str
    study_id: int | None = None
    error: str | None = None


class ChannelQcOut(BaseModel):
    channel_id: int
    name: str
    signal_type: str | None
    missing_pct: float
    flatline_pct: float
    clipping_pct: float
    drift_score: float
    artifact_pct: float
    score: float
    label: str
    issues: list[str]


class StudyQcOut(BaseModel):
    study_id: int
    overall_score: float
    overall_label: str
    channels: list[ChannelQcOut]


class SignalWindowOut(BaseModel):
    channel_id: int
    start_sec: float
    end_sec: float
    sampling_rate: float
    """Effective spacing between returned points, in seconds — 1/sampling_rate
    when unsampled, larger when the window was downsampled for the response."""
    point_interval_sec: float
    t: list[float]
    v: list[float]
