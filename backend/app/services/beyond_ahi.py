"""Beyond AHI (README top-level positioning; frontend spec §18 "Beyond AHI"):
puts the single AHI number in context by placing it side by side with
oxygen, arousal, autonomic, and recovery burden — explicitly framed as
*exploring* physiology alongside AHI, never as a replacement for it.

Every dimension here is a straight aggregation of numbers other pipeline
stages already computed (respiratory_events, oxygen_burden, brain_response,
autonomic_response) — no new detection or scoring happens in this module,
and a dimension with no matching channel is reported unavailable, never
filled in with an invented number.
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models.respiratory_event import RespiratoryEvent
from app.db.models.study import Study
from app.services.oxygen_burden.analysis import clean_spo2, compute_oxygen_summary
from app.services.respiratory_events.pipeline import (
    ensure_eeg_enriched,
    ensure_hr_enriched,
    get_or_detect_events,
    pick_spo2_channel,
)
from app.storage import get_storage


@dataclass
class BurdenMetric:
    available: bool
    value: float | None
    message: str | None = None


@dataclass
class BeyondAhiResult:
    ahi: BurdenMetric
    odi: BurdenMetric
    oxygen_time_below_90: BurdenMetric
    oxygen_mean_desaturation: BurdenMetric
    arousal_burden: BurdenMetric
    autonomic_burden: BurdenMetric
    recovery_burden: BurdenMetric


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 3) if values else None


def compute_beyond_ahi(db: Session, study: Study) -> tuple[BeyondAhiResult, list[RespiratoryEvent]] | None:
    resp_channel, events = get_or_detect_events(db, study)
    if resp_channel is None:
        return None

    duration_hr = (study.duration_sec or 0) / 3600
    ahi = BurdenMetric(True, round(len(events) / duration_hr, 2) if duration_hr > 0 else 0.0)

    spo2_channel = pick_spo2_channel(study.channels)
    if spo2_channel is not None:
        spo2_samples, artifact_pct = clean_spo2(get_storage().get_array(spo2_channel.storage_key))
        oxygen_summary = compute_oxygen_summary(spo2_samples, spo2_channel.sampling_rate, artifact_pct)
        odi = BurdenMetric(True, oxygen_summary.odi)
        oxygen_time_below_90 = BurdenMetric(True, oxygen_summary.pct_time_below_90)

        desat_values = [e.desaturation_depth for e in events if e.desaturation_depth is not None]
        oxygen_mean_desaturation = BurdenMetric(bool(desat_values), _mean(desat_values))
        recovery_values = [e.recovery_sec for e in events if e.recovery_sec is not None]
        recovery_burden = BurdenMetric(bool(recovery_values), _mean(recovery_values))
    else:
        no_spo2 = "No SpO2 channel is mapped for this study."
        odi = BurdenMetric(False, None, no_spo2)
        oxygen_time_below_90 = BurdenMetric(False, None, no_spo2)
        oxygen_mean_desaturation = BurdenMetric(False, None, no_spo2)
        recovery_burden = BurdenMetric(False, None, no_spo2)

    eeg_channel = ensure_eeg_enriched(db, study, events)
    if eeg_channel is not None:
        arousal_values = [e.arousal_probability for e in events if e.arousal_probability is not None]
        arousal_burden = BurdenMetric(bool(arousal_values), _mean(arousal_values))
    else:
        arousal_burden = BurdenMetric(False, None, "No EEG channel is mapped for this study.")

    ecg_channel = ensure_hr_enriched(db, study, events)
    if ecg_channel is not None:
        hr_values = [e.hr_response_bpm for e in events if e.hr_response_bpm is not None]
        autonomic_burden = BurdenMetric(bool(hr_values), _mean(hr_values))
    else:
        autonomic_burden = BurdenMetric(False, None, "No ECG channel is mapped for this study.")

    result = BeyondAhiResult(
        ahi=ahi,
        odi=odi,
        oxygen_time_below_90=oxygen_time_below_90,
        oxygen_mean_desaturation=oxygen_mean_desaturation,
        arousal_burden=arousal_burden,
        autonomic_burden=autonomic_burden,
        recovery_burden=recovery_burden,
    )
    return result, events
