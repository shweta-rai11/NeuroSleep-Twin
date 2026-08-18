"""Hypnogram derived from a dataset's own ground-truth stage annotations —
MIT-BIH PSG '.st' epoch codes, or an Apple Health export's own sleep-stage
classification — an "Observed measurement" per the README's labeling
scheme, not a model output of ours. There is no EEG-based auto-stager yet
(that is real future work); studies without recognizable stage annotations
simply report no hypnogram rather than a fabricated one.

Apple Watch's stages come from its own accelerometer+heart-rate algorithm,
not EEG, and it doesn't distinguish N1 from N2 (both land in "Core") — a
real difference in provenance from the PSG-derived stages, not just a
different code table. Callers that care can still tell them apart via each
epoch's annotation source, kept as "apple_health_sleep" through ingestion.
"""

from dataclasses import dataclass

from app.db.models.annotation import Annotation

# R&K-era codes used by MIT-BIH PSG's '.st' annotations, remapped to modern
# AASM stage names (3 and 4 merge into N3; MT = movement time / artifact).
_STAGE_CODE_MAP = {
    "W": "Wake", "0": "Wake",
    "1": "N1",
    "2": "N2",
    "3": "N3", "4": "N3",
    "R": "REM",
    "MT": "Movement",
}

_VALID_STAGES = {"Wake", "N1", "N2", "N3", "REM", "Movement"}


@dataclass
class StageEpoch:
    onset_sec: float
    duration_sec: float
    stage: str


def parse_hypnogram(annotations: list[Annotation]) -> list[StageEpoch]:
    epochs = []
    for ann in annotations:
        if ann.source == "st":
            code = ann.label.strip().split(" ")[0]
            stage = _STAGE_CODE_MAP.get(code)
        elif ann.source == "apple_health_sleep":
            # Ingestion already maps to this app's stage vocabulary directly.
            stage = ann.label if ann.label in _VALID_STAGES else None
        else:
            continue
        if stage is None:
            continue
        epochs.append(StageEpoch(onset_sec=ann.onset_sec, duration_sec=ann.duration_sec, stage=stage))
    return sorted(epochs, key=lambda e: e.onset_sec)
