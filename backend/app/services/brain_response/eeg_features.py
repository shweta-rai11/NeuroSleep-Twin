"""Event-centered EEG spectral response (README §14/§15). Relative band
power via Welch PSD — a "Derived physiological metric" from a disclosed
formula — plus a heuristic arousal-probability proxy from the pre/post
power shift, explicitly a "Machine-learning estimate": it is NOT AASM
arousal scoring (which requires trained visual scoring of a ≥3s frequency
shift) and must never be presented as one. Described as "cortical
electrophysiological response" — never a claim about anatomical
localization (README top-of-file rules).
"""

from dataclasses import dataclass

import numpy as np
from scipy import signal

BANDS = {"delta": (0.5, 4.0), "theta": (4.0, 8.0), "alpha": (8.0, 13.0), "beta": (13.0, 30.0)}

BASELINE_LOOKBACK_SEC = 30.0
RESPONSE_WINDOW_SEC = 15.0  # immediately following event end, where arousal-linked shifts concentrate
MIN_WINDOW_SEC = 2.0


@dataclass
class EegEventFeatures:
    delta_rel: float | None
    theta_rel: float | None
    alpha_rel: float | None
    beta_rel: float | None
    arousal_probability: float | None


def _relative_band_power(window: np.ndarray, fs: float) -> dict[str, float] | None:
    if len(window) < fs * MIN_WINDOW_SEC:
        return None
    freqs, psd = signal.welch(window, fs=fs, nperseg=min(len(window), int(fs * 4)))
    total_mask = (freqs >= 0.5) & (freqs <= 30)
    total_power = float(np.trapezoid(psd[total_mask], freqs[total_mask]))
    if total_power <= 0:
        return None
    return {
        name: float(np.trapezoid(psd[(freqs >= lo) & (freqs < hi)], freqs[(freqs >= lo) & (freqs < hi)]) / total_power)
        for name, (lo, hi) in BANDS.items()
    }


def compute_eeg_event_features(eeg: np.ndarray, fs: float, onset_sec: float, duration_sec: float) -> EegEventFeatures:
    baseline_start = max(0, int((onset_sec - BASELINE_LOOKBACK_SEC) * fs))
    baseline_end = int(onset_sec * fs)
    response_start = int((onset_sec + duration_sec) * fs)
    response_end = min(len(eeg), int((onset_sec + duration_sec + RESPONSE_WINDOW_SEC) * fs))

    baseline_power = _relative_band_power(eeg[baseline_start:baseline_end], fs)
    response_power = _relative_band_power(eeg[response_start:response_end], fs)

    if response_power is None:
        return EegEventFeatures(None, None, None, None, None)

    arousal_probability = None
    if baseline_power is not None:
        shift = (response_power["alpha"] + response_power["beta"]) - (baseline_power["alpha"] + baseline_power["beta"])
        arousal_probability = round(float(1 / (1 + np.exp(-8 * shift))), 4)

    return EegEventFeatures(
        round(response_power["delta"], 4), round(response_power["theta"], 4),
        round(response_power["alpha"], 4), round(response_power["beta"], 4),
        arousal_probability,
    )
