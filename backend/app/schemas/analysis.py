from pydantic import BaseModel, ConfigDict


class RespiratoryEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    onset_sec: float
    duration_sec: float
    event_type: str
    depth_ratio: float
    spo2_baseline: float | None
    spo2_nadir: float | None
    desaturation_depth: float | None
    desaturation_slope: float | None
    recovery_sec: float | None
    eeg_delta_rel: float | None
    eeg_theta_rel: float | None
    eeg_alpha_rel: float | None
    eeg_beta_rel: float | None
    arousal_probability: float | None
    hr_baseline_bpm: float | None
    hr_peak_bpm: float | None
    hr_response_bpm: float | None


class RespiratoryEventSummary(BaseModel):
    count: int
    apnea_count: int
    hypopnea_count: int
    events_per_hour: float


class ChannelRef(BaseModel):
    id: int
    name: str


class RespiratoryEventsOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    channel_used: ChannelRef | None
    algorithm_version: str | None
    summary: RespiratoryEventSummary | None
    events: list[RespiratoryEventOut]


class OxygenSummaryOut(BaseModel):
    mean_spo2: float
    min_spo2: float
    pct_time_below_90: float
    odi: float
    artifact_pct: float


class OxygenBurdenOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    channel_used: ChannelRef | None
    summary: OxygenSummaryOut | None
    events: list[RespiratoryEventOut]


class EventFeatureResultOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    channel_used: ChannelRef | None
    events: list[RespiratoryEventOut]


class StageEpochOut(BaseModel):
    onset_sec: float
    duration_sec: float
    stage: str


class SleepStagesOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    epochs: list[StageEpochOut]
    stage_minutes: dict[str, float]


class BurdenMetricOut(BaseModel):
    available: bool
    value: float | None
    message: str | None


class BeyondAhiOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    ahi: BurdenMetricOut | None
    odi: BurdenMetricOut | None
    oxygen_time_below_90: BurdenMetricOut | None
    oxygen_mean_desaturation: BurdenMetricOut | None
    arousal_burden: BurdenMetricOut | None
    autonomic_burden: BurdenMetricOut | None
    recovery_burden: BurdenMetricOut | None


class AcousticPauseOut(BaseModel):
    onset_sec: float
    duration_sec: float
    depth_ratio: float


class AcousticSummaryOut(BaseModel):
    pause_count: int
    pauses_per_hour: float
    mean_pause_duration_sec: float
    pct_time_in_pause: float


class AcousticAnalysisOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    channel_used: ChannelRef | None
    summary: AcousticSummaryOut | None
    pauses: list[AcousticPauseOut]
