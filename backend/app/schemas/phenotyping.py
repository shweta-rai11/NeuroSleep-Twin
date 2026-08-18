from pydantic import BaseModel


class ClusterOut(BaseModel):
    cluster_index: int
    label: str
    size: int
    centroid: list[float]


class PhenotypeEventOut(BaseModel):
    event_id: int
    study_id: int
    study_label: str
    onset_sec: float
    event_type: str
    cluster_index: int
    fingerprint: list[float]


class PhenotypesOut(BaseModel):
    available: bool
    message: str | None
    k: int
    axes: list[str]
    clusters: list[ClusterOut]
    events: list[PhenotypeEventOut]


class LabelUpdate(BaseModel):
    label: str
