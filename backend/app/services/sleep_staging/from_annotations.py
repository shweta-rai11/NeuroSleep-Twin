"""Hypnogram derived from a dataset's own ground-truth stage annotations
(MIT-BIH PSG '.st' epoch codes) — an "Observed measurement" per the
README's labeling scheme, not a model output. There is no EEG-based
auto-stager yet (that is real future work); studies without recognizable
stage annotations simply report no hypnogram rather than a fabricated one.
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


@dataclass
class StageEpoch:
    onset_sec: float
    duration_sec: float
    stage: str


def parse_hypnogram(annotations: list[Annotation]) -> list[StageEpoch]:
    epochs = []
    for ann in annotations:
        if ann.source != "st":
            continue
        code = ann.label.strip().split(" ")[0]
        stage = _STAGE_CODE_MAP.get(code)
        if stage is None:
            continue
        epochs.append(StageEpoch(onset_sec=ann.onset_sec, duration_sec=ann.duration_sec, stage=stage))
    return sorted(epochs, key=lambda e: e.onset_sec)
