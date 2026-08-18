"""Imports one night's data from an Apple Health export (Health app ->
profile icon -> Export All Health Data -> export.zip). This is a
fundamentally different data source from the rest of the app: Apple Watch's
sleep stages are that device's own accelerometer+heart-rate algorithm, not
EEG — and heart rate / SpO2 / respiratory rate are irregular spot-check
samples, not a continuous physiological waveform. They are:

  - Sleep stages: imported as Annotations (source="apple_health_sleep"),
    stage names already mapped to this app's vocabulary — feeds the
    existing Sleep Staging page directly, labeled as an observed
    measurement (Apple's own classification, not ours).
  - Heart rate / SpO2 / respiratory rate: linearly resampled onto a coarse
    fixed grid and stored as ordinary Channels so they show up in the
    Signal Viewer, but deliberately left with signal_type=None (unmapped)
    so they are never fed into the ECG-R-peak or continuous-pulse-ox
    pipelines built for actual physiological sensors — that would produce
    fine-grained "events" from data that's really a few spot-checks per
    hour.

One export.xml can span years, so ingestion is two calls: scan (find each
contiguous sleep session) and import_night (extract just one).
"""

import shutil
import uuid
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy.orm import Session

from app.db.models.annotation import Annotation
from app.db.models.channel import Channel
from app.db.models.study import Study
from app.storage import get_storage

DATASET_ID = "apple-health"

SESSION_GAP_SEC = 3600  # a >1h gap between sleep records starts a new "night"
RESAMPLE_INTERVAL_SEC = 60.0  # coarse grid for HR/SpO2/RespRate — these are spot-checks, not continuous

_SLEEP_STAGE_MAP = {
    "HKCategoryValueSleepAnalysisAwake": "Wake",
    "HKCategoryValueSleepAnalysisAsleepCore": "N2",  # Apple doesn't split N1 out — Core covers both
    "HKCategoryValueSleepAnalysisAsleepDeep": "N3",
    "HKCategoryValueSleepAnalysisAsleepREM": "REM",
    "HKCategoryValueSleepAnalysisAsleepUnspecified": "N2",  # asleep but Watch couldn't classify further
}

_QUANTITY_TYPES = {
    "HKQuantityTypeIdentifierHeartRate": ("Heart Rate (Apple Watch)", "bpm", 1.0),
    "HKQuantityTypeIdentifierOxygenSaturation": ("Blood Oxygen (Apple Watch)", "%", 100.0),
    "HKQuantityTypeIdentifierRespiratoryRate": ("Respiratory Rate (Apple Watch)", "breaths/min", 1.0),
}


class AppleHealthImportError(ValueError):
    pass


def _parse_dt(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S %z")


@dataclass
class SleepSession:
    index: int
    start: datetime
    end: datetime
    record_count: int

    @property
    def duration_hours(self) -> float:
        return (self.end - self.start).total_seconds() / 3600


@dataclass
class ScanResult:
    source_id: str
    sessions: list[SleepSession] = field(default_factory=list)


def _source_dir(source_id: str) -> Path:
    from app.storage import REPO_ROOT

    d = REPO_ROOT / "data" / "uploads" / "apple-health" / source_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_export(filename: str, content: bytes) -> str:
    """Saves the uploaded export (zip or raw xml) and returns a source_id
    that scan()/import_night() use to find it again."""
    source_id = uuid.uuid4().hex
    d = _source_dir(source_id)

    if filename.lower().endswith(".zip"):
        zip_path = d / "export.zip"
        zip_path.write_bytes(content)
        try:
            with zipfile.ZipFile(zip_path) as zf:
                xml_name = next((n for n in zf.namelist() if n.endswith("export.xml")), None)
                if xml_name is None:
                    raise AppleHealthImportError("No export.xml found inside the uploaded zip.")
                with zf.open(xml_name) as src, open(d / "export.xml", "wb") as dst:
                    shutil.copyfileobj(src, dst)
        except zipfile.BadZipFile as exc:
            raise AppleHealthImportError("Uploaded file isn't a valid zip archive.") from exc
        zip_path.unlink()
    elif filename.lower().endswith(".xml"):
        (d / "export.xml").write_bytes(content)
    else:
        raise AppleHealthImportError("Expected export.zip or export.xml from the Health app.")

    return source_id


def _xml_path(source_id: str) -> Path:
    path = _source_dir(source_id) / "export.xml"
    if not path.exists():
        raise AppleHealthImportError(f"No Apple Health export found for '{source_id}'.")
    return path


def scan_sleep_sessions(source_id: str) -> ScanResult:
    records: list[tuple[datetime, datetime]] = []
    for _, elem in ET.iterparse(_xml_path(source_id), events=("end",)):
        if elem.tag == "Record" and elem.get("type") == "HKCategoryTypeIdentifierSleepAnalysis":
            if elem.get("value") != "HKCategoryValueSleepAnalysisInBed":
                records.append((_parse_dt(elem.get("startDate")), _parse_dt(elem.get("endDate"))))
        elem.clear()

    if not records:
        return ScanResult(source_id=source_id, sessions=[])

    records.sort()
    sessions: list[SleepSession] = []
    current = [records[0]]
    for start, end in records[1:]:
        if (start - current[-1][1]).total_seconds() > SESSION_GAP_SEC:
            sessions.append(SleepSession(len(sessions), current[0][0], current[-1][1], len(current)))
            current = [(start, end)]
        else:
            current.append((start, end))
    sessions.append(SleepSession(len(sessions), current[0][0], current[-1][1], len(current)))

    return ScanResult(source_id=source_id, sessions=sorted(sessions, key=lambda s: s.start, reverse=True))


def _resample_channel(samples: list[tuple[float, float]], duration_sec: float) -> tuple[np.ndarray, float] | None:
    """samples: (offset_sec, value) pairs, unsorted, possibly with duplicate
    timestamps. Returns (resampled_array, sampling_rate) or None if too
    sparse to resample."""
    if len(samples) < 2:
        return None
    samples = sorted(samples)
    xs = np.array([s[0] for s in samples])
    ys = np.array([s[1] for s in samples])
    grid = np.arange(0, duration_sec, RESAMPLE_INTERVAL_SEC)
    if len(grid) < 2:
        return None
    resampled = np.interp(grid, xs, ys)
    return resampled, 1.0 / RESAMPLE_INTERVAL_SEC


def import_night(db: Session, study: Study, source_id: str, session_start: datetime, session_end: datetime) -> None:
    duration_sec = (session_end - session_start).total_seconds()

    stage_annotations: list[Annotation] = []
    quantity_samples: dict[str, list[tuple[float, float]]] = {t: [] for t in _QUANTITY_TYPES}

    for _, elem in ET.iterparse(_xml_path(source_id), events=("end",)):
        if elem.tag != "Record":
            continue
        record_type = elem.get("type")

        if record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            value = elem.get("value")
            stage = _SLEEP_STAGE_MAP.get(value)
            if stage is not None:
                start = _parse_dt(elem.get("startDate"))
                end = _parse_dt(elem.get("endDate"))
                if start < session_end and end > session_start:
                    onset = max(0.0, (start - session_start).total_seconds())
                    epoch_duration = (end - start).total_seconds()
                    stage_annotations.append(
                        Annotation(study_id=study.id, onset_sec=onset, duration_sec=epoch_duration,
                                   label=stage, source="apple_health_sleep")
                    )
        elif record_type in _QUANTITY_TYPES:
            start = _parse_dt(elem.get("startDate"))
            if session_start <= start <= session_end:
                _, _, scale = _QUANTITY_TYPES[record_type]
                try:
                    value = float(elem.get("value")) * scale
                except (TypeError, ValueError):
                    elem.clear()
                    continue
                offset = (start - session_start).total_seconds()
                quantity_samples[record_type].append((offset, value))

        elem.clear()

    storage = get_storage()
    channel_idx = 0
    for record_type, (channel_name, unit, _scale) in _QUANTITY_TYPES.items():
        result = _resample_channel(quantity_samples[record_type], duration_sec)
        if result is None:
            continue
        resampled, fs = result
        storage_key = f"studies/{study.id}/ch{channel_idx}"
        storage.put_array(storage_key, resampled)
        db.add(
            Channel(
                study_id=study.id, name=channel_name, signal_type=None, mapping_confidence=0.0,
                unit=unit, sampling_rate=fs, n_samples=len(resampled), storage_key=storage_key,
            )
        )
        channel_idx += 1

    if channel_idx == 0:
        # Always keep at least one channel so the rest of the app (viewer,
        # QC, ...) has something to show — an all-annotations study with no
        # channels doesn't fit the existing data model.
        placeholder = np.zeros(max(2, int(duration_sec / RESAMPLE_INTERVAL_SEC)), dtype=np.float32)
        storage_key = f"studies/{study.id}/ch0"
        storage.put_array(storage_key, placeholder)
        db.add(
            Channel(study_id=study.id, name="(no heart rate/SpO2/respiratory data for this night)",
                    signal_type=None, mapping_confidence=0.0, unit=None,
                    sampling_rate=1.0 / RESAMPLE_INTERVAL_SEC, n_samples=len(placeholder), storage_key=storage_key)
        )

    db.add_all(stage_annotations)
    study.duration_sec = duration_sec
