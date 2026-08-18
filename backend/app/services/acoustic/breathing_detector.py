"""Acoustic breathing-pause detection from a single-channel audio recording
(voice memo / phone video) — NOT part of the EEG/ECG/SpO2-derived pipeline
and much weaker evidence than it.

This is a "Machine-learning estimate" per the README's labeling scheme, at
best. A phone mic is not a calibrated physiological sensor: room noise,
mic placement, and blankets all change the recording completely, and quiet
normal breathing is acoustically indistinguishable from a real pause —
detection is only meaningful relative to an already-established audible
baseline (e.g. snoring) in the same recording. There is no ground truth to
benchmark this against, unlike the PSG-derived respiratory detector. Never
present this as apnea detection or any kind of diagnosis.

Same underlying idea as app/services/respiratory_events/detector.py
(sustained envelope drop vs. local baseline = candidate event), reimplemented
with a frame-based RMS envelope rather than a per-sample rolling window —
a full night of audio is 50-100x more samples than a physiological channel
at its native rate, so a naive rolling window is too slow.

Normal breathing is itself acoustically bimodal — loud during inhale/snore,
near-silent between breaths, cycling every ~3-6s — which a naive envelope
would misread as "sustained quiet" the instant a rolling-median baseline's
window happens to contain more quiet frames than loud ones. A rolling-MAX
smoothing pass over one breathing-cycle's worth of time (ACTIVITY_WINDOW_SEC)
turns that into a stable "was there activity nearby" signal that only drops
across a real multi-breath gap, not a normal breath's own quiet half.
"""

from dataclasses import dataclass

import numpy as np

FRAME_SEC = 0.5
ACTIVITY_WINDOW_SEC = 6.0  # >= one full breathing cycle, so a normal breath's quiet half never reads as "activity gone"
BASELINE_WINDOW_FRAMES = 180  # 90s of frames, at FRAME_SEC=0.5
MIN_PAUSE_SEC = 10.0
MAX_PAUSE_SEC = 120.0
PAUSE_RATIO = 0.2
MERGE_GAP_SEC = 2.0


@dataclass
class AcousticPause:
    onset_sec: float
    duration_sec: float
    depth_ratio: float


def _frame_rms_envelope(samples: np.ndarray, fs: float, frame_sec: float) -> np.ndarray:
    frame_size = max(1, int(fs * frame_sec))
    n_frames = len(samples) // frame_size
    trimmed = samples[: n_frames * frame_size].reshape(n_frames, frame_size)
    return np.sqrt(np.mean(trimmed.astype(np.float64) ** 2, axis=1))


def _rolling_median(values: np.ndarray, window: int) -> np.ndarray:
    import pandas as pd

    return pd.Series(values).rolling(window=window, min_periods=1, center=True).median().to_numpy()


def _rolling_max(values: np.ndarray, window: int) -> np.ndarray:
    import pandas as pd

    return pd.Series(values).rolling(window=window, min_periods=1, center=True).max().to_numpy()


def detect_acoustic_pauses(samples: np.ndarray, fs: float) -> tuple[list[AcousticPause], np.ndarray, float]:
    """Returns (pauses, activity_envelope, frame_sec) — the (already
    max-smoothed) envelope is returned too so callers can show it without
    recomputing."""
    raw_envelope = _frame_rms_envelope(samples, fs, FRAME_SEC)
    if len(raw_envelope) < BASELINE_WINDOW_FRAMES:
        return [], raw_envelope, FRAME_SEC

    activity_window_frames = max(1, int(ACTIVITY_WINDOW_SEC / FRAME_SEC))
    envelope = _rolling_max(raw_envelope, activity_window_frames)

    baseline = _rolling_median(envelope, BASELINE_WINDOW_FRAMES)
    ratio = envelope / (baseline + 1e-6)

    below = ratio < PAUSE_RATIO
    idx = np.where(below)[0]
    if idx.size == 0:
        return [], envelope, FRAME_SEC

    merge_gap_frames = int(MERGE_GAP_SEC / FRAME_SEC)
    min_frames = int(MIN_PAUSE_SEC / FRAME_SEC)
    max_frames = int(MAX_PAUSE_SEC / FRAME_SEC)

    pauses: list[AcousticPause] = []
    run_start = idx[0]
    prev = idx[0]
    for i in idx[1:]:
        if i - prev > merge_gap_frames:
            pauses.extend(_finalize_run(run_start, prev, ratio, min_frames, max_frames))
            run_start = i
        prev = i
    pauses.extend(_finalize_run(run_start, prev, ratio, min_frames, max_frames))

    return pauses, envelope, FRAME_SEC


def _finalize_run(start: int, end: int, ratio: np.ndarray, min_frames: int, max_frames: int) -> list[AcousticPause]:
    length = end - start + 1
    if length < min_frames or length > max_frames:
        return []
    min_ratio = float(np.min(ratio[start : end + 1]))
    return [
        AcousticPause(
            onset_sec=float(start * FRAME_SEC),
            duration_sec=float(length * FRAME_SEC),
            depth_ratio=round(min_ratio, 4),
        )
    ]
