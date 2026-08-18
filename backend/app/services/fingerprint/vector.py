"""The event fingerprint (README §13): a fixed, disclosed 0-1 normalization
of each event's raw feature columns, not a learned embedding. Mirrors the
frontend's radar-chart axes (src/components/fingerprint/computeFingerprint.ts)
so the same definition drives both the visualization and the phenotype
clustering (Phase 12).
"""

from app.db.models.respiratory_event import RespiratoryEvent

FINGERPRINT_AXES = ["severity", "duration", "desaturation", "hr_response", "arousal"]


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def fingerprint_vector(event: RespiratoryEvent) -> list[float]:
    return [
        _clip01(1 - event.depth_ratio),
        _clip01(event.duration_sec / 60),
        _clip01(event.desaturation_depth / 30) if event.desaturation_depth is not None else 0.0,
        _clip01(event.hr_response_bpm / 40) if event.hr_response_bpm is not None else 0.0,
        event.arousal_probability if event.arousal_probability is not None else 0.0,
    ]
