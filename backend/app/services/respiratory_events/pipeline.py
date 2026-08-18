from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.respiratory_event import RespiratoryEvent
from app.db.models.study import Study
from app.services.autonomic_response.hr_features import (
    compute_hr_event_features,
    detect_r_peaks,
    instantaneous_hr_series,
)
from app.services.brain_response.eeg_features import compute_eeg_event_features
from app.services.oxygen_burden.analysis import clean_spo2, enrich_event_with_oxygen
from app.services.respiratory_events.detector import ALGORITHM_VERSION, detect_events, prepare_resp_signal
from app.storage import get_storage

_RESP_TYPE_PRIORITY = ["resp", "airflow", "effort"]


def pick_primary_resp_channel(channels: list[Channel]) -> Channel | None:
    for signal_type in _RESP_TYPE_PRIORITY:
        for ch in channels:
            if ch.signal_type == signal_type:
                return ch
    return None


def pick_spo2_channel(channels: list[Channel]) -> Channel | None:
    for ch in channels:
        if ch.signal_type == "spo2":
            return ch
    return None


def pick_eeg_channel(channels: list[Channel]) -> Channel | None:
    for ch in channels:
        if ch.signal_type == "eeg":
            return ch
    return None


def pick_ecg_channel(channels: list[Channel]) -> Channel | None:
    for ch in channels:
        if ch.signal_type == "ecg":
            return ch
    return None


def pick_audio_channel(channels: list[Channel]) -> Channel | None:
    for ch in channels:
        if ch.signal_type == "audio":
            return ch
    return None


def get_or_detect_events(db: Session, study: Study) -> tuple[Channel | None, list[RespiratoryEvent]]:
    resp_channel = pick_primary_resp_channel(study.channels)
    if resp_channel is None:
        return None, []

    existing = [e for e in study.respiratory_events if e.algorithm_version == ALGORITHM_VERSION]
    if existing:
        return resp_channel, sorted(existing, key=lambda e: e.onset_sec)

    storage = get_storage()
    resp_samples = prepare_resp_signal(storage.get_array(resp_channel.storage_key), resp_channel.sampling_rate)
    candidates = detect_events(resp_samples, resp_channel.sampling_rate)

    spo2_channel = pick_spo2_channel(study.channels)
    spo2_samples = clean_spo2(storage.get_array(spo2_channel.storage_key))[0] if spo2_channel else None

    rows: list[RespiratoryEvent] = []
    for c in candidates:
        oxygen = (
            enrich_event_with_oxygen(c, spo2_samples, spo2_channel.sampling_rate)
            if spo2_samples is not None and spo2_channel is not None
            else None
        )
        rows.append(
            RespiratoryEvent(
                study_id=study.id,
                channel_id=resp_channel.id,
                algorithm_version=ALGORITHM_VERSION,
                onset_sec=c.onset_sec,
                duration_sec=c.duration_sec,
                event_type=c.event_type,
                depth_ratio=c.depth_ratio,
                spo2_baseline=oxygen.spo2_baseline if oxygen else None,
                spo2_nadir=oxygen.spo2_nadir if oxygen else None,
                desaturation_depth=oxygen.desaturation_depth if oxygen else None,
                desaturation_slope=oxygen.desaturation_slope if oxygen else None,
                recovery_sec=oxygen.recovery_sec if oxygen else None,
            )
        )
    db.add_all(rows)
    db.commit()
    for row in rows:
        db.refresh(row)
    return resp_channel, sorted(rows, key=lambda e: e.onset_sec)


def ensure_eeg_enriched(db: Session, study: Study, events: list[RespiratoryEvent]) -> Channel | None:
    """Populates each event's EEG band-power / arousal-probability columns
    in place, once. A no-op (fast) on every call after the first."""
    eeg_channel = pick_eeg_channel(study.channels)
    if eeg_channel is None or not events:
        return eeg_channel
    if all(e.eeg_delta_rel is not None for e in events):
        return eeg_channel

    eeg_samples = get_storage().get_array(eeg_channel.storage_key)
    for event in events:
        if event.eeg_delta_rel is not None:
            continue
        features = compute_eeg_event_features(eeg_samples, eeg_channel.sampling_rate, event.onset_sec, event.duration_sec)
        event.eeg_delta_rel = features.delta_rel
        event.eeg_theta_rel = features.theta_rel
        event.eeg_alpha_rel = features.alpha_rel
        event.eeg_beta_rel = features.beta_rel
        event.arousal_probability = features.arousal_probability
    db.commit()
    return eeg_channel


def ensure_hr_enriched(db: Session, study: Study, events: list[RespiratoryEvent]) -> Channel | None:
    """Populates each event's HR-response columns in place, once. R-peaks
    are detected across the whole ECG channel a single time and reused for
    every event, rather than re-run per event."""
    ecg_channel = pick_ecg_channel(study.channels)
    if ecg_channel is None or not events:
        return ecg_channel
    if all(e.hr_baseline_bpm is not None for e in events):
        return ecg_channel

    ecg_samples = get_storage().get_array(ecg_channel.storage_key)
    r_peaks = detect_r_peaks(ecg_samples, ecg_channel.sampling_rate)
    times, bpm = instantaneous_hr_series(r_peaks, ecg_channel.sampling_rate)

    for event in events:
        if event.hr_baseline_bpm is not None:
            continue
        features = compute_hr_event_features(times, bpm, event.onset_sec, event.duration_sec)
        event.hr_baseline_bpm = features.hr_baseline_bpm
        event.hr_peak_bpm = features.hr_peak_bpm
        event.hr_response_bpm = features.hr_response_bpm
    db.commit()
    return ecg_channel
