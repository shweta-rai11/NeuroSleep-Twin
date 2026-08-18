from pydantic import BaseModel


class NightSummaryOut(BaseModel):
    study_id: int
    record_name: str
    duration_sec: float
    events_per_hour: float | None
    mean_spo2: float | None
    odi: float | None
    stage_pct: dict[str, float]


class PatientGroupOut(BaseModel):
    patient_key: str
    nights: list[NightSummaryOut]


class LongitudinalOut(BaseModel):
    available: bool
    message: str | None
    patients: list[PatientGroupOut]
