from pydantic import BaseModel


class SleepSessionOut(BaseModel):
    index: int
    start: str
    end: str
    duration_hours: float
    record_count: int


class ScanResultOut(BaseModel):
    source_id: str
    sessions: list[SleepSessionOut]
