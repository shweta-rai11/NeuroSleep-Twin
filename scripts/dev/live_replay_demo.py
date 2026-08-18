"""Live Replay demo server — NOT part of the NeuroSleep Twin application.

Answers one question for pitch purposes: "can I show this working live,
without a PSG device in the room?" It streams a REAL, previously recorded
MIT-BIH Polysomnographic Database study (PhysioNet) through the project's
actual event-detection / oxygen / autonomic / EEG feature code
(backend/app/services/...), chunk by chunk, at an adjustable speed
multiplier — so a real night's worth of apnea events, fingerprints, and
recovery dynamics appear on screen as if watching it happen live.

It is a simulated replay of real recorded data, not a live patient feed —
the frontend says so explicitly, consistent with this project's own
labeling rules (README "Research Prototype — read this first").

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
from app.services.respiratory_events.detector import CandidateEvent, detect_events  # noqa: E402

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

FINGERPRINT_AXES = ["severity", "duration", "desaturation", "hr_response", "arousal"]

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


def load_record(record_id: str) -> dict:
    """Cached after first download so the actual pitch demo never depends
    on the room having internet."""
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


def _build_event_payload(
    candidate: CandidateEvent,
    fs: float,
    ecg: np.ndarray | None,
    eeg: np.ndarray | None,
    spo2_clean: np.ndarray | None,
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
        "fingerprint": {"axes": FINGERPRINT_AXES, "values": [round(v, 4) for v in fingerprint]},
    }


app = FastAPI(title="NeuroSleep Twin — Live Replay Demo")


@app.get("/api/records")
def list_records():
    return [
        {**rec, "cached": (CACHE_DIR / f"{rec['id']}.npz").exists()}
        for rec in CURATED_RECORDS
    ]


@app.get("/", response_class=HTMLResponse)
def index():
    return FRONTEND_PATH.read_text()


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
    resp, ecg, eeg, spo2 = data.get("resp"), data.get("ecg"), data.get("eeg"), data.get("spo2")
    if resp is None:
        await websocket.send_json({"type": "error", "message": f"{record_id} has no respiratory channel"})
        await websocket.close()
        return

    spo2_clean = None
    if spo2 is not None:
        spo2_clean, _artifact_pct = clean_spo2(spo2)

    duration_sec = len(resp) / fs
    await websocket.send_json(
        {
            "type": "ready",
            "record": record_id,
            "duration_sec": duration_sec,
            "fs": fs,
            "channels": [name for name, arr in (("eeg", eeg), ("ecg", ecg), ("resp", resp), ("spo2", spo2)) if arr is not None],
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
                for name, arr in (("eeg", eeg), ("ecg", ecg), ("resp", resp), ("spo2", spo2)):
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
                await websocket.send_json(_build_event_payload(candidate, fs, ecg, eeg, spo2_clean))

            if new_events_this_scan:
                state["fast_forward"] = False

            stats = {"type": "stats", "elapsed_sim_sec": round(sim_time, 1), "n_events": len(emitted)}
            if spo2_clean is not None:
                stats["oxygen"] = asdict(compute_oxygen_summary(spo2_clean[:idx], fs))
            await websocket.send_json(stats)

        await websocket.send_json({"type": "done"})
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        receiver_task.cancel()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8090)
