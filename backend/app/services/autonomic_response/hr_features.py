"""Event-centered heart-rate response (README §16) from an ECG-derived
R-peak series — a lightweight Pan-Tompkins-style detector, not a validated
beat annotator. Framed as "cardiovascular signal changes," never as direct
measurement of autonomic nervous system nuclei (README top-of-file rules).
"""

from dataclasses import dataclass

import numpy as np
from scipy import signal

BASELINE_LOOKBACK_SEC = 30.0
RESPONSE_WINDOW_SEC = 20.0  # HR surge typically follows arousal at event termination
MIN_PHYSIOLOGIC_BPM = 30.0
MAX_PHYSIOLOGIC_BPM = 220.0


def detect_r_peaks(ecg: np.ndarray, fs: float) -> np.ndarray:
    sos = signal.butter(3, [5, 15], btype="bandpass", fs=fs, output="sos")
    filtered = signal.sosfiltfilt(sos, ecg)
    derivative = np.diff(filtered, prepend=filtered[0])
    squared = derivative**2
    window = max(1, int(0.15 * fs))
    integrated = np.convolve(squared, np.ones(window) / window, mode="same")

    min_distance = max(1, int(60 / MAX_PHYSIOLOGIC_BPM * fs))
    threshold = float(np.mean(integrated) + 0.5 * np.std(integrated))
    peaks, _ = signal.find_peaks(integrated, distance=min_distance, height=threshold)
    return peaks


def instantaneous_hr_series(r_peaks: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray]:
    """Returns (time_sec, bpm) — one HR sample per R-R interval, timestamped
    at the second peak, with physiologically-implausible intervals dropped
    (a missed/spurious peak, not a real heartbeat)."""
    if len(r_peaks) < 2:
        return np.array([]), np.array([])
    rr_sec = np.diff(r_peaks) / fs
    bpm = 60 / rr_sec
    times = r_peaks[1:] / fs
    valid = (bpm >= MIN_PHYSIOLOGIC_BPM) & (bpm <= MAX_PHYSIOLOGIC_BPM)
    return times[valid], bpm[valid]


@dataclass
class HrEventFeatures:
    hr_baseline_bpm: float | None
    hr_peak_bpm: float | None
    hr_response_bpm: float | None


def compute_hr_event_features(times: np.ndarray, bpm: np.ndarray, onset_sec: float, duration_sec: float) -> HrEventFeatures:
    if times.size == 0:
        return HrEventFeatures(None, None, None)

    baseline_mask = (times >= onset_sec - BASELINE_LOOKBACK_SEC) & (times < onset_sec)
    response_mask = (times >= onset_sec) & (times < onset_sec + duration_sec + RESPONSE_WINDOW_SEC)

    if not baseline_mask.any() or not response_mask.any():
        return HrEventFeatures(None, None, None)

    baseline_bpm = float(np.mean(bpm[baseline_mask]))
    peak_bpm = float(np.max(bpm[response_mask]))
    return HrEventFeatures(round(baseline_bpm, 1), round(peak_bpm, 1), round(peak_bpm - baseline_bpm, 1))
