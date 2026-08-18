"""Research signal-quality assessment (README §5 "QC / readiness score") —
computed live from the stored waveform, never a clinical-quality
certification. Flags missingness, flatline runs, clipping/saturation,
baseline drift, and extreme-outlier artifacts, then rolls them into a single
0-100 readiness score per channel.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

FLATLINE_WINDOW_SEC = 1.0
CLIP_EPSILON_FRACTION = 1e-6
ARTIFACT_Z_THRESHOLD = 6.0


@dataclass
class ChannelQc:
    channel_id: int
    name: str
    signal_type: str | None
    missing_pct: float
    flatline_pct: float
    clipping_pct: float
    drift_score: float
    artifact_pct: float
    score: float
    label: str
    issues: list[str] = field(default_factory=list)


def _label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Fair"
    return "Poor"


def compute_channel_qc(channel_id: int, name: str, signal_type: str | None, samples: np.ndarray, fs: float) -> ChannelQc:
    n = len(samples)
    missing_mask = ~np.isfinite(samples)
    missing_pct = float(missing_mask.mean()) if n else 1.0

    clean = samples[~missing_mask] if missing_mask.any() else samples

    if clean.size < 2:
        return ChannelQc(
            channel_id, name, signal_type, missing_pct * 100, 100.0, 0.0, 0.0, 0.0, 0.0, "Poor",
            issues=["No usable samples."],
        )

    window = max(2, int(fs * FLATLINE_WINDOW_SEC))
    rolling_std = pd.Series(clean).rolling(window=window, min_periods=window).std().to_numpy()
    overall_std = float(np.std(clean))
    flat_threshold = max(overall_std * 1e-4, 1e-9)
    valid_windows = rolling_std[~np.isnan(rolling_std)]
    flatline_pct = float((valid_windows < flat_threshold).mean()) if valid_windows.size else 0.0

    lo, hi = float(np.min(clean)), float(np.max(clean))
    span = max(hi - lo, 1e-9)
    clip_eps = span * CLIP_EPSILON_FRACTION
    clipping_pct = float(((clean <= lo + clip_eps) | (clean >= hi - clip_eps)).mean())

    tenth = max(1, clean.size // 10)
    baseline_start = float(np.mean(clean[:tenth]))
    baseline_end = float(np.mean(clean[-tenth:]))
    drift_score = abs(baseline_end - baseline_start) / (overall_std + 1e-9)

    z = (clean - np.mean(clean)) / (overall_std + 1e-9)
    artifact_pct = float((np.abs(z) > ARTIFACT_Z_THRESHOLD).mean())

    score = 100.0
    score -= missing_pct * 100 * 0.6
    score -= flatline_pct * 100 * 0.4
    score -= clipping_pct * 100 * 0.4
    score -= min(drift_score * 8, 20)
    score -= artifact_pct * 100 * 0.6
    score = max(0.0, min(100.0, score))

    issues = []
    if missing_pct > 0.01:
        issues.append(f"{missing_pct * 100:.1f}% missing/non-finite samples.")
    if flatline_pct > 0.05:
        issues.append(f"{flatline_pct * 100:.1f}% of the recording looks flat (sensor may have been off).")
    if clipping_pct > 0.02:
        issues.append(f"{clipping_pct * 100:.1f}% of samples sit at the signal's min/max — possible clipping.")
    if drift_score > 1.0:
        issues.append("Baseline drifts noticeably between start and end of recording.")
    if artifact_pct > 0.005:
        issues.append(f"{artifact_pct * 100:.2f}% of samples are extreme outliers (|z| > {ARTIFACT_Z_THRESHOLD:.0f}).")

    return ChannelQc(
        channel_id, name, signal_type,
        round(missing_pct * 100, 3), round(flatline_pct * 100, 3), round(clipping_pct * 100, 3),
        round(drift_score, 3), round(artifact_pct * 100, 4), round(score, 1), _label(score), issues,
    )
