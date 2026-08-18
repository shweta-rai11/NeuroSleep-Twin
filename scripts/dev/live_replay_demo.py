"""Live Replay server — NOT part of the NeuroSleep Twin application.

Two record sources feed the same viewer:

1. PhysioNet MIT-BIH PSG recordings — a real previously-recorded study,
   played back at speed for pitch/demo purposes (see start_live_demo.sh).
2. Your own recordings from personal-sleep-tracker/recorder.html — a phone
   microphone (breathing/snore-sound envelope) + motion sensor, saved as
   CSV under personal-sleep-tracker/recordings/. There is no SpO2/ECG/EEG
   in that case, so oxygen/HR/EEG-derived fields are simply absent — never
   filled in with invented numbers.

Both sources run through the SAME event-detection / oxygen / autonomic /
EEG feature code the app itself uses (backend/app/services/...), chunk by
chunk, at an adjustable speed multiplier, so events and fingerprints
appear on screen as if watching them happen live.

Standalone on purpose: no Postgres, no Redis, no Celery. Just this process
plus a browser, so it is one thing that can go wrong instead of five.

Run:
    scripts/dev/start_live_demo.sh
    open http://localhost:8090
"""

import asyncio
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
import uvicorn
import wfdb
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.autonomic_response.hr_features import (  # noqa: E402
    compute_hr_event_features,
    detect_r_peaks,
    instantaneous_hr_series,
)
from app.services.brain_response.eeg_features import compute_eeg_event_features  # noqa: E402
from app.services.channel_mapping import guess_signal_type  # noqa: E402
from app.services.oxygen_burden.analysis import (  # noqa: E402
    clean_spo2,
    compute_oxygen_summary,
    enrich_event_with_oxygen,
)
from app.services.respiratory_events.detector import CandidateEvent, detect_events, prepare_resp_signal  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("live_replay_demo")

PN_DIR = "slpdb/1.0.0"
CACHE_DIR = REPO_ROOT / "data" / "datasets" / "mitbih-psg" / "raw"
FRONTEND_PATH = Path(__file__).with_name("live_replay_demo.html")

# Curated for the demo specifically: every record here has ECG + EEG + a
# respiratory-effort channel + SpO2, so all four response channels the
# pitch talks about actually have something to show. Full slpdb catalog
# has 18 records; most lack SpO2 and were left out on purpose.
CURATED_RECORDS = [
    {"id": "slp67x", "label": "slp67x — 77 min (fastest to load)", "duration_min": 77},
    {"id": "slp59", "label": "slp59 — 240 min", "duration_min": 240},
    {"id": "slp66", "label": "slp66 — 220 min", "duration_min": 220},
    {"id": "slp60", "label": "slp60 — 355 min (full night)", "duration_min": 355},
]
DEFAULT_RECORD = CURATED_RECORDS[0]["id"]

PERSONAL_PREFIX = "personal:"
PERSONAL_DIR = REPO_ROOT / "personal-sleep-tracker" / "recordings"
PERSONAL_SAMPLE_HZ = 4.0  # matches recorder.html's 250ms sampling interval

# Every channel this server knows how to stream/detect on, in fixed
# display order. "motion" only ever comes from a personal recording.
CHANNEL_ORDER = ("eeg", "ecg", "resp", "spo2", "motion")

FINGERPRINT_AXES = ["severity", "duration", "desaturation", "hr_response", "arousal"]

# AASM severity bands, by events/hour — the same bands the cited studies
# below use for AHI. IMPORTANT: the "events/hour" this app computes is
# this project's own envelope-v1 candidate-event rate (README: "not a
# clinical scorer"), not a manually-scored clinical AHI. Mapping it onto
# these bands is a convenience for reading the cited research, not a claim
# that this tool measures AHI. Every figure below is a verified reported
# statistic from the cited study, not an estimate — if a study reported a
# non-significant result, that's stated, not omitted.
SEVERITY_BANDS = [(5.0, "normal"), (15.0, "mild"), (30.0, "moderate"), (float("inf"), "severe")]

CV_RESEARCH_CONTEXT = {
    "normal": [],
    "mild": [
        {
            "study": "Peppard et al., NEJM 2000 (Wisconsin Sleep Cohort)",
            "finding": "AHI 5.0-14.9 at baseline was associated with roughly 2x the odds of incident hypertension 4 years later (OR 2.03, 95% CI 1.29-3.17) vs. AHI 0.",
            "url": "https://www.nejm.org/doi/full/10.1056/NEJM200005113421901",
        },
    ],
    "moderate": [
        {
            "study": "Peppard et al., NEJM 2000 (Wisconsin Sleep Cohort)",
            "finding": "AHI ≥15 at baseline was associated with roughly 2.9x the odds of incident hypertension 4 years later (OR 2.89, 95% CI 1.46-5.64) vs. AHI 0.",
            "url": "https://www.nejm.org/doi/full/10.1056/NEJM200005113421901",
        },
        {
            "study": "Punjabi et al., PLoS Medicine 2009 (Sleep Heart Health Study, n=6,441)",
            "finding": "Moderate SDB (AHI 15-29.9) trended toward higher all-cause mortality (HR 1.17, 95% CI 0.97-1.42) vs. AHI<5 — reported as NOT statistically significant on its own.",
            "url": "https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1000132",
        },
    ],
    "severe": [
        {
            "study": "Marin et al., Lancet 2005",
            "finding": "Untreated severe OSA was associated with roughly 2.9x the odds of a fatal (OR 2.87, 95% CI 1.17-7.51) and 3.2x a non-fatal (OR 3.17, 95% CI 1.12-7.51) cardiovascular event vs. healthy men, over long-term follow-up.",
            "url": "https://www.thelancet.com/journals/lancet/article/PIIS0140-6736(05)71141-7/abstract",
        },
        {
            "study": "Punjabi et al., PLoS Medicine 2009 (Sleep Heart Health Study, n=6,441)",
            "finding": "Severe SDB (AHI ≥30) was associated with 1.46x all-cause mortality (HR 1.46, 95% CI 1.14-1.86) vs. AHI<5; in men aged 40-70 specifically, HR 2.09 (95% CI 1.31-3.33).",
            "url": "https://journals.plos.org/plosmedicine/article?id=10.1371/journal.pmed.1000132",
        },
        {
            "study": "Shahar et al., AJRCCM 2001 (Sleep Heart Health Study, n=6,424)",
            "finding": "The highest AHI quartile was associated with 2.4x the odds of prevalent heart failure (OR 2.38, 95% CI 1.22-4.62) vs. the lowest quartile.",
            "url": "https://www.atsjournals.org/doi/full/10.1164/ajrccm.163.1.2001008",
        },
    ],
}


def _severity_band(events_per_hour: float) -> str:
    for threshold, label in SEVERITY_BANDS:
        if events_per_hour < threshold:
            return label
    return "severe"

TICK_SEC = 0.2  # wall-clock pacing granularity
SCAN_INTERVAL_WALL_SEC = 5.0  # how often we re-run event detection on the buffer so far
FINALIZE_MARGIN_SEC = 25.0  # let the detector's own rolling-baseline edge settle before trusting an event
FAST_FORWARD_MULTIPLIER = 20  # "skip to next event" — for keeping a live pitch on schedule


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def fingerprint_vector(
    depth_ratio: float,
    duration_sec: float,
    desaturation_depth: float | None,
    hr_response_bpm: float | None,
    arousal_probability: float | None,
) -> list[float]:
    """Same 5-axis, 0-1 normalization as app/services/fingerprint/vector.py
    — duplicated here in plain-float form because that version reads off a
    SQLAlchemy ORM row, which doesn't exist in this standalone demo."""
    return [
        _clip01(1 - depth_ratio),
        _clip01(duration_sec / 60),
        _clip01(desaturation_depth / 30) if desaturation_depth is not None else 0.0,
        _clip01(hr_response_bpm / 40) if hr_response_bpm is not None else 0.0,
        arousal_probability if arousal_probability is not None else 0.0,
    ]


# guess_signal_type() distinguishes "resp" (a generic respiration channel)
# from "airflow" (nasal/thermistor) and "effort" (chest/abdominal belt) —
# a real distinction the app cares about, but for this demo's single
# amplitude-envelope detector any one of them works as "the breathing
# channel." slpdb records almost always label theirs "Resp (nasal)" or
# "Resp (chest)", which the mapper classifies as airflow/effort respectively.
RESP_LIKE_TYPES = ("resp", "airflow", "effort")


def _pick_channels(sig_names: list[str]) -> dict[str, int]:
    picked: dict[str, int] = {}
    for i, name in enumerate(sig_names):
        signal_type, _confidence = guess_signal_type(name)
        if signal_type in RESP_LIKE_TYPES and "resp" not in picked:
            picked["resp"] = i
        elif signal_type in ("ecg", "eeg", "spo2") and signal_type not in picked:
            picked[signal_type] = i
    return picked


def _list_personal_recordings() -> list[dict]:
    if not PERSONAL_DIR.exists():
        return []
    out = []
    for csv_path in sorted(PERSONAL_DIR.glob("*.csv"), reverse=True):
        try:
            n_rows = sum(1 for _ in csv_path.open()) - 1  # minus header
        except OSError:
            continue
        duration_min = round(n_rows / PERSONAL_SAMPLE_HZ / 60, 1)
        out.append(
            {
                "id": f"{PERSONAL_PREFIX}{csv_path.stem}",
                "label": f"{csv_path.stem} — {duration_min} min",
                "duration_min": duration_min,
                "personal": True,
            }
        )
    return out


def _load_personal_recording(record_id: str) -> dict:
    stem = record_id[len(PERSONAL_PREFIX):]
    csv_path = PERSONAL_DIR / f"{stem}.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"no recording named {stem} in {PERSONAL_DIR}")

    df = pd.read_csv(csv_path)
    duration_sec = float(df["t_sec"].iloc[-1])
    n_samples = int(duration_sec * PERSONAL_SAMPLE_HZ) + 1
    grid = np.arange(n_samples) / PERSONAL_SAMPLE_HZ

    result: dict = {"fs": PERSONAL_SAMPLE_HZ}
    # recorder.html samples on a fixed setInterval tick but real device
    # timing jitters — interpolate onto a strictly uniform grid so the
    # (fs-in-seconds) window constants in detect_events()/etc. line up.
    audio = np.interp(grid, df["t_sec"], df["audio_rms"]).astype(np.float32)
    result["resp"] = prepare_resp_signal(audio, PERSONAL_SAMPLE_HZ)
    if "motion_mag" in df.columns:
        result["motion"] = np.interp(grid, df["t_sec"], df["motion_mag"]).astype(np.float32)
    return result


def load_record(record_id: str) -> dict:
    """Cached after first download so the actual pitch demo never depends
    on the room having internet."""
    if record_id.startswith(PERSONAL_PREFIX):
        return _load_personal_recording(record_id)

    cache_path = CACHE_DIR / f"{record_id}.npz"
    if cache_path.exists():
        logger.info("loading %s from local cache", record_id)
        npz = np.load(cache_path)
        return {k: (float(npz[k]) if k == "fs" else npz[k]) for k in npz.files}

    logger.info("downloading %s from PhysioNet (one-time)...", record_id)
    record = wfdb.rdrecord(record_id, pn_dir=PN_DIR)
    channel_idx = _pick_channels(record.sig_name)

    result: dict = {"fs": float(record.fs)}
    save_kwargs: dict = {"fs": np.float64(record.fs)}
    for signal_type in ("ecg", "eeg", "resp", "spo2"):
        if signal_type in channel_idx:
            arr = record.p_signal[:, channel_idx[signal_type]].astype(np.float32)
            result[signal_type] = arr
            save_kwargs[signal_type] = arr

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(cache_path, **save_kwargs)
    logger.info("cached %s -> %s", record_id, cache_path)
    return result


def _decimate_envelope(segment: np.ndarray, n_buckets: int) -> list[list[float]]:
    """[min, max] per bucket — cheap enough for every websocket tick, and
    keeps ECG spikes / apnea flattening visible even though we're only
    sending a handful of points per channel per tick."""
    if segment.size == 0:
        return []
    n_buckets = max(1, min(n_buckets, segment.size))
    buckets = np.array_split(segment, n_buckets)
    return [[round(float(b.min()), 4), round(float(b.max()), 4)] for b in buckets if b.size]


MOTION_BASELINE_SEC = 30.0
MOTION_RESPONSE_SEC = 30.0


def _motion_response(motion: np.ndarray, fs: float, onset: float, duration: float) -> dict | None:
    """Not part of the app's fingerprint definition — there's no ORM/DB
    concept of a 'motion' response, because the app was designed around
    physiological sensors, not a phone accelerometer. Reported as its own
    field so it's never confused with the EEG-derived arousal_probability."""
    baseline_start = max(0, int((onset - MOTION_BASELINE_SEC) * fs))
    baseline_end = int(onset * fs)
    response_start = baseline_end
    response_end = min(len(motion), int((onset + duration + MOTION_RESPONSE_SEC) * fs))
    baseline_window = motion[baseline_start:baseline_end]
    response_window = motion[response_start:response_end]
    if baseline_window.size == 0 or response_window.size == 0:
        return None
    baseline = float(np.mean(baseline_window))
    response = float(np.mean(response_window))
    return {"baseline": round(baseline, 4), "response": round(response, 4), "delta": round(response - baseline, 4)}


def _build_event_payload(
    candidate: CandidateEvent,
    fs: float,
    ecg: np.ndarray | None,
    eeg: np.ndarray | None,
    spo2_clean: np.ndarray | None,
    motion: np.ndarray | None = None,
) -> dict:
    onset, duration = candidate.onset_sec, candidate.duration_sec

    oxygen = None
    if spo2_clean is not None:
        oxygen = enrich_event_with_oxygen(candidate, spo2_clean, fs)

    hr = None
    if ecg is not None:
        window_start = max(0, int((onset - 30) * fs))
        window_end = min(len(ecg), int((onset + duration + 60) * fs))
        ecg_window = ecg[window_start:window_end]
        r_peaks = detect_r_peaks(ecg_window, fs)
        times, bpm = instantaneous_hr_series(r_peaks, fs)
        times = times + window_start / fs  # back to record-absolute time
        hr = compute_hr_event_features(times, bpm, onset, duration)

    eeg_features = None
    if eeg is not None:
        eeg_features = compute_eeg_event_features(eeg, fs, onset, duration)

    movement = _motion_response(motion, fs, onset, duration) if motion is not None else None

    fingerprint = fingerprint_vector(
        depth_ratio=candidate.depth_ratio,
        duration_sec=duration,
        desaturation_depth=oxygen.desaturation_depth if oxygen else None,
        hr_response_bpm=hr.hr_response_bpm if hr else None,
        arousal_probability=eeg_features.arousal_probability if eeg_features else None,
    )

    return {
        "type": "event",
        "onset_sec": round(onset, 1),
        "duration_sec": round(duration, 1),
        "event_type": candidate.event_type,
        "depth_ratio": candidate.depth_ratio,
        "oxygen": asdict(oxygen) if oxygen else None,
        "hr": asdict(hr) if hr else None,
        "eeg": asdict(eeg_features) if eeg_features else None,
        "movement": movement,
        "fingerprint": {"axes": FINGERPRINT_AXES, "values": [round(v, 4) for v in fingerprint]},
    }


app = FastAPI(title="NeuroSleep Twin — Live Replay")


@app.get("/api/records")
def list_records():
    physionet = [
        {**rec, "cached": (CACHE_DIR / f"{rec['id']}.npz").exists(), "personal": False}
        for rec in CURATED_RECORDS
    ]
    return _list_personal_recordings() + physionet


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_PATH.read_text()


RECORDER_PATH = REPO_ROOT / "personal-sleep-tracker" / "recorder.html"


@app.get("/recorder", response_class=HTMLResponse)
def recorder():
    """Fallback path for the phone recorder if AirDrop/local-file opening
    doesn't grant microphone access on your phone's browser: open
    http://<this-computer's-LAN-IP>:8090/recorder from the phone instead.
    Note this is still plain HTTP, not HTTPS, so some browsers may still
    block the microphone for a non-localhost origin — see
    personal-sleep-tracker/README.md for the HTTPS-tunnel fallback."""
    return RECORDER_PATH.read_text()


@app.websocket("/ws/replay")
async def ws_replay(websocket: WebSocket):
    await websocket.accept()
    try:
        init = await websocket.receive_json()
    except Exception:
        await websocket.close()
        return

    record_id = init.get("record") or DEFAULT_RECORD
    state = {"speed": float(init.get("speed", 40)), "paused": False, "fast_forward": False}

    await websocket.send_json({"type": "loading", "record": record_id})
    try:
        data = await asyncio.to_thread(load_record, record_id)
    except Exception as exc:  # noqa: BLE001 — surfaced to the demo UI, not a server crash
        logger.exception("failed to load record %s", record_id)
        await websocket.send_json({"type": "error", "message": f"Couldn't load {record_id}: {exc}"})
        await websocket.close()
        return

    fs = data["fs"]
    eeg, ecg, resp, spo2, motion = (data.get(name) for name in CHANNEL_ORDER)
    if resp is None:
        await websocket.send_json({"type": "error", "message": f"{record_id} has no respiratory/breathing channel"})
        await websocket.close()
        return

    spo2_clean = None
    if spo2 is not None:
        spo2_clean, _artifact_pct = clean_spo2(spo2)

    source = "personal" if record_id.startswith(PERSONAL_PREFIX) else "physionet"
    duration_sec = len(resp) / fs
    await websocket.send_json(
        {
            "type": "ready",
            "record": record_id,
            "source": source,
            "duration_sec": duration_sec,
            "fs": fs,
            "channels": [name for name in CHANNEL_ORDER if data.get(name) is not None],
        }
    )

    async def receiver():
        while True:
            msg = await websocket.receive_json()
            if msg.get("type") != "control":
                continue
            if "speed" in msg:
                state["speed"] = float(msg["speed"])
            if "paused" in msg:
                state["paused"] = bool(msg["paused"])
            if msg.get("fast_forward_to_next_event"):
                state["fast_forward"] = True

    receiver_task = asyncio.create_task(receiver())

    try:
        sim_time = 0.0
        prev_idx = 0
        last_scan_wall = 0.0
        elapsed_wall = 0.0
        emitted: set[float] = set()

        while sim_time < duration_sec:
            await asyncio.sleep(TICK_SEC)
            if state["paused"]:
                continue

            effective_speed = state["speed"] * (FAST_FORWARD_MULTIPLIER if state["fast_forward"] else 1)
            sim_time = min(duration_sec, sim_time + TICK_SEC * effective_speed)
            elapsed_wall += TICK_SEC
            idx = int(sim_time * fs)

            if idx > prev_idx:
                batch = {"type": "wave", "t": round(sim_time, 2)}
                span = idx - prev_idx
                n_buckets = max(1, min(30, span // 4 or 1))
                for name, arr in zip(CHANNEL_ORDER, (eeg, ecg, resp, spo2, motion)):
                    if arr is None:
                        continue
                    batch[name] = _decimate_envelope(arr[prev_idx:idx], n_buckets)
                await websocket.send_json(batch)
                prev_idx = idx

            if elapsed_wall - last_scan_wall < SCAN_INTERVAL_WALL_SEC:
                continue
            last_scan_wall = elapsed_wall

            candidates = detect_events(resp[:idx], fs)
            new_events_this_scan = 0
            for candidate in candidates:
                key = round(candidate.onset_sec, 1)
                if key in emitted:
                    continue
                if candidate.onset_sec + candidate.duration_sec + FINALIZE_MARGIN_SEC > sim_time:
                    continue  # rolling-baseline edge hasn't settled yet — wait for more data
                emitted.add(key)
                new_events_this_scan += 1
                await websocket.send_json(_build_event_payload(candidate, fs, ecg, eeg, spo2_clean, motion))

            if new_events_this_scan:
                state["fast_forward"] = False

            stats = {"type": "stats", "elapsed_sim_sec": round(sim_time, 1), "n_events": len(emitted)}
            if spo2_clean is not None:
                stats["oxygen"] = asdict(compute_oxygen_summary(spo2_clean[:idx], fs))

            elapsed_hours = sim_time / 3600
            if elapsed_hours > 0:
                events_per_hour = len(emitted) / elapsed_hours
                band = _severity_band(events_per_hour)
                stats["cv_context"] = {
                    "events_per_hour": round(events_per_hour, 1),
                    "severity": band,
                    "associations": CV_RESEARCH_CONTEXT[band],
                }
            await websocket.send_json(stats)

        await websocket.send_json({"type": "done"})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        receiver_task.cancel()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
