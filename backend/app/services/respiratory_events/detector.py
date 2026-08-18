"""Candidate respiratory-event (apnea/hypopnea) detector.

A pragmatic amplitude-envelope detector, not a clinical scorer: it flags
sustained drops in a respiratory-effort/airflow channel's envelope relative
to its own local baseline, using AASM's minimum 10s event duration as a
floor. Output is a "Machine-learning estimate" per the README's labeling
scheme — a candidate, to be benchmarked against ground-truth annotations
where available (Phase 13), never presented as a diagnosis.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

ALGORITHM_VERSION = "envelope-v1"

MIN_EVENT_SEC = 10.0
MAX_EVENT_SEC = 120.0  # beyond this it's almost certainly a baseline/sensor artifact, not one event
ENVELOPE_WINDOW_SEC = 2.0
BASELINE_WINDOW_SEC = 100.0
HYPOPNEA_RATIO = 0.7   # envelope < 70% of local baseline
APNEA_RATIO = 0.15     # envelope < 15% of local baseline
MERGE_GAP_SEC = 2.0    # bridge short gaps between below-threshold runs

PROXY_DETREND_WINDOW_SEC = 4.0


def prepare_resp_signal(samples: np.ndarray, fs: float) -> np.ndarray:
    """detect_events() below looks for drops in *deviation from the
    signal's own median* — correct for a real respiratory-effort/airflow
    channel, which is AC-coupled and oscillates around zero all night
    (confirmed on MIT-BIH PSG: e.g. a "Resp (abdominal)" channel ranges
    roughly -1.3 to 0.8). A strictly non-negative signal — e.g. a
    microphone RMS/loudness reading from personal-sleep-tracker's
    recorder.html, which can never go below 0 — doesn't have that shape:
    its "median" sits inside the normal-breathing range, so a silent
    apnea reads as a LARGER deviation from the median, not a smaller one
    — backwards from what the detector expects. If the signal never goes
    negative, subtract a short rolling mean first so it oscillates around
    zero on every breath and goes flat during a pause, same as a real
    effort channel. A real physiological channel (already negative-going)
    passes through unchanged."""
    if float(np.min(samples)) >= 0:
        window = max(2, int(fs * PROXY_DETREND_WINDOW_SEC))
        local_mean = pd.Series(samples).rolling(window=window, min_periods=1, center=True).mean().to_numpy()
        return (samples - local_mean).astype(samples.dtype if np.issubdtype(samples.dtype, np.floating) else np.float32)
    return samples


@dataclass
class CandidateEvent:
    onset_sec: float
    duration_sec: float
    event_type: str  # "apnea" | "hypopnea"
    depth_ratio: float


def _envelope(samples: np.ndarray, fs: float) -> np.ndarray:
    rectified = np.abs(samples - np.median(samples))
    window = max(2, int(fs * ENVELOPE_WINDOW_SEC))
    return pd.Series(rectified).rolling(window=window, min_periods=1, center=True).mean().to_numpy()


def _baseline(envelope: np.ndarray, fs: float) -> np.ndarray:
    window = max(2, int(fs * BASELINE_WINDOW_SEC))
    # A rolling *median* (not mean) so the baseline itself isn't dragged down by the
    # apneas/hypopneas it's meant to be judging against.
    return pd.Series(envelope).rolling(window=window, min_periods=1, center=True).median().to_numpy()


def detect_events(samples: np.ndarray, fs: float) -> list[CandidateEvent]:
    if len(samples) < fs * MIN_EVENT_SEC:
        return []

    envelope = _envelope(samples, fs)
    baseline = _baseline(envelope, fs)
    ratio = envelope / (baseline + 1e-9)

    below = ratio < HYPOPNEA_RATIO
    events: list[CandidateEvent] = []

    # Merge below-threshold samples into runs, bridging short gaps.
    merge_gap_samples = int(MERGE_GAP_SEC * fs)
    idx = np.where(below)[0]
    if idx.size == 0:
        return []

    run_start = idx[0]
    prev = idx[0]
    for i in idx[1:]:
        if i - prev > merge_gap_samples:
            events.extend(_finalize_run(run_start, prev, ratio, fs))
            run_start = i
        prev = i
    events.extend(_finalize_run(run_start, prev, ratio, fs))

    return events


def _finalize_run(start: int, end: int, ratio: np.ndarray, fs: float) -> list[CandidateEvent]:
    duration_sec = (end - start + 1) / fs
    if duration_sec < MIN_EVENT_SEC or duration_sec > MAX_EVENT_SEC:
        return []
    min_ratio = float(np.min(ratio[start : end + 1]))
    event_type = "apnea" if min_ratio < APNEA_RATIO else "hypopnea"
    return [
        CandidateEvent(
            onset_sec=float(start / fs),
            duration_sec=float(duration_sec),
            event_type=event_type,
            depth_ratio=round(min_ratio, 4),
        )
    ]
