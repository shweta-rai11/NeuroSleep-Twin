"""Oxygen burden: per-event desaturation features, plus a study-level
summary independent of any detected respiratory event (mean/min SpO2, an
oxygen desaturation index (ODI), and time spent below 90%). All "Derived
physiological metric" per the README's labeling scheme — computed with a
fixed, disclosed formula, not a model.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.services.respiratory_events.detector import CandidateEvent

BASELINE_LOOKBACK_SEC = 15.0
NADIR_SEARCH_AFTER_SEC = 45.0  # desaturation nadir typically lags event end
RECOVERY_SEARCH_SEC = 60.0
RECOVERY_THRESHOLD_FRACTION = 0.9  # "recovered" once back within 90% of the desaturation depth

ODI_DIP_PCT = 3.0
ODI_MIN_GAP_SEC = 10.0

# Real pulse-oximetry channels carry sensor-dropout/artifact runs that don't
# always land on an obviously-invalid sentinel — the same MIT-BIH PSG
# recording that produced negative and >100 values also ramped smoothly
# down toward 0 during a dropout, which a plain [0, 100] filter would let
# through as a "real" reading. True SpO2 essentially never falls below 50%
# even in severe apnea, so this floor is a disclosed, fixed threshold for
# rejecting dropout, not a physiological claim about the lowest survivable
# saturation.
VALID_SPO2_RANGE = (50.0, 100.0)


def clean_spo2(spo2: np.ndarray) -> tuple[np.ndarray, float]:
    """Replaces out-of-range samples via forward/backward fill so indices —
    and therefore time alignment against event onsets — are unchanged.
    Returns (cleaned_array, pct_of_samples_replaced) so callers can disclose
    how much of the channel was dropout rather than a real reading."""
    lo, hi = VALID_SPO2_RANGE
    valid = (spo2 >= lo) & (spo2 <= hi)
    series = pd.Series(np.where(valid, spo2, np.nan))
    cleaned = series.ffill().bfill().to_numpy()
    artifact_pct = float((~valid).mean() * 100)
    return cleaned, artifact_pct


@dataclass
class OxygenEventFeatures:
    spo2_baseline: float | None
    spo2_nadir: float | None
    desaturation_depth: float | None
    desaturation_slope: float | None
    recovery_sec: float | None


def enrich_event_with_oxygen(event: CandidateEvent, spo2: np.ndarray, fs_spo2: float) -> OxygenEventFeatures:
    onset_idx = int(event.onset_sec * fs_spo2)
    end_idx = int((event.onset_sec + event.duration_sec) * fs_spo2)

    baseline_start = max(0, onset_idx - int(BASELINE_LOOKBACK_SEC * fs_spo2))
    baseline_window = spo2[baseline_start:onset_idx]
    if baseline_window.size == 0:
        return OxygenEventFeatures(None, None, None, None, None)
    baseline = float(np.median(baseline_window))

    search_end = min(len(spo2), end_idx + int(NADIR_SEARCH_AFTER_SEC * fs_spo2))
    search_window = spo2[onset_idx:search_end]
    if search_window.size == 0:
        return OxygenEventFeatures(baseline, None, None, None, None)

    nadir_offset = int(np.argmin(search_window))
    nadir = float(search_window[nadir_offset])
    depth = baseline - nadir
    time_to_nadir_sec = nadir_offset / fs_spo2
    slope = depth / time_to_nadir_sec if time_to_nadir_sec > 0 else None

    recovery_sec = None
    if depth > 0:
        recovery_target = nadir + depth * RECOVERY_THRESHOLD_FRACTION
        recovery_search_end = min(len(spo2), onset_idx + nadir_offset + int(RECOVERY_SEARCH_SEC * fs_spo2))
        recovery_window = spo2[onset_idx + nadir_offset : recovery_search_end]
        recovered = np.where(recovery_window >= recovery_target)[0]
        if recovered.size > 0:
            recovery_sec = float(recovered[0] / fs_spo2)

    return OxygenEventFeatures(
        round(baseline, 2), round(nadir, 2), round(depth, 2),
        round(slope, 4) if slope is not None else None, recovery_sec,
    )


@dataclass
class OxygenSummary:
    mean_spo2: float
    min_spo2: float
    pct_time_below_90: float
    odi: float  # independent 3%-dip events per hour
    artifact_pct: float  # share of raw samples that were sensor dropout, replaced before these stats


def compute_oxygen_summary(spo2: np.ndarray, fs: float, artifact_pct: float = 0.0) -> OxygenSummary:
    duration_hr = len(spo2) / fs / 3600
    mean_spo2 = float(np.mean(spo2))
    min_spo2 = float(np.min(spo2))
    pct_below_90 = float(np.mean(spo2 < 90) * 100)

    # Simple local-maximum dip counter: walk forward tracking the running max
    # (recent baseline); a `>= ODI_DIP_PCT` drop from that max, followed by
    # recovery back near it, counts as one desaturation event. SpO2 dynamics
    # are slow (seconds), so this runs on a 1Hz decimation of the signal —
    # both much faster than a per-sample Python loop and less sensitive to
    # sensor noise than the native sampling rate.
    decimation = max(1, int(fs))
    decimated = spo2[::decimation]
    decimated_fs = fs / decimation

    running_max = decimated[0]
    in_dip = False
    dip_start_level = decimated[0]
    last_dip_end_idx = -1e18
    odi_count = 0
    min_gap_samples = ODI_MIN_GAP_SEC * decimated_fs

    for i, value in enumerate(decimated):
        if not in_dip:
            running_max = max(running_max, value)
            if running_max - value >= ODI_DIP_PCT and i - last_dip_end_idx >= min_gap_samples:
                in_dip = True
                dip_start_level = running_max
        else:
            if value >= dip_start_level - 0.5:  # recovered to within 0.5% of the pre-dip level
                in_dip = False
                last_dip_end_idx = i
                odi_count += 1
                running_max = value

    odi = odi_count / duration_hr if duration_hr > 0 else 0.0
    return OxygenSummary(
        round(mean_spo2, 2), round(min_spo2, 2), round(pct_below_90, 2), round(odi, 2), round(artifact_pct, 2)
    )
