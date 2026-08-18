"""Ingests a user-uploaded sleep study — EDF/EDF+, WFDB (as a .zip bundle of
its record files), or CSV+JSON. This is Phase 3's real upload pipeline; it
shares the same Channel/Annotation storage shape as the public MIT-BIH
ingestion (app/services/ingestion/mitbih.py) so every later pipeline stage
(QC, staging, event detection, ...) is format-agnostic from here on.
"""

import csv as csv_module
import json
import logging
import shutil
import zipfile
from pathlib import Path

import mne
import numpy as np
import wfdb
from sqlalchemy.orm import Session

from app.db.models.annotation import Annotation
from app.db.models.channel import Channel
from app.db.models.study import Study
from app.services.channel_mapping import guess_signal_type
from app.storage import get_storage

logger = logging.getLogger(__name__)

DATASET_ID = "user-upload"

# Accepted upload extensions. Anything else is rejected before it ever
# touches disk (README §11: file-type validation gates all uploads).
ALLOWED_EXTENSIONS = {".edf", ".csv", ".json", ".zip", ".hea", ".dat"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500MB — generous for a night of PSG, still bounded


class UnsupportedUploadError(ValueError):
    pass


def detect_format(filenames: list[str]) -> str:
    lowered = [f.lower() for f in filenames]
    if any(f.endswith(".edf") for f in lowered):
        return "edf"
    if any(f.endswith(".zip") for f in lowered):
        return "wfdb_zip"
    if any(f.endswith(".hea") for f in lowered):
        return "wfdb"
    if any(f.endswith(".csv") for f in lowered) and any(f.endswith(".json") for f in lowered):
        return "csv_json"
    raise UnsupportedUploadError(
        "Unrecognized upload — provide an EDF/EDF+ file, a WFDB record (.hea/.dat, "
        "optionally zipped), or a CSV of samples plus a JSON metadata file."
    )


def validate_filenames(filenames: list[str]) -> None:
    for name in filenames:
        ext = Path(name).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise UnsupportedUploadError(f"File type '{ext or name}' is not accepted for upload.")


def validate_file_signature(filename: str, content: bytes) -> None:
    """Checks the file's actual leading bytes against what its extension
    claims (README §11: file-type validation gates all uploads) — this is
    signature verification, not a substitute for real malware/AV scanning,
    which this deployment does not run."""
    ext = Path(filename).suffix.lower()
    if ext == ".edf" and not (content[:1] == b"0" and content[1:8].strip(b" ") == b""):
        raise UnsupportedUploadError(f"'{filename}' doesn't look like a real EDF file (bad header).")
    if ext == ".zip" and content[:4] not in (b"PK\x03\x04", b"PK\x05\x06"):
        raise UnsupportedUploadError(f"'{filename}' doesn't look like a real zip archive (bad header).")
    if ext == ".json":
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            raise UnsupportedUploadError(f"'{filename}' is not valid JSON.") from exc


def _write_channels_and_annotations(
    db: Session,
    study: Study,
    channel_names: list[str],
    units: list[str | None],
    fs: float,
    data: np.ndarray,  # shape (n_channels, n_samples)
    annotations: list[tuple[float, float, str]],  # (onset_sec, duration_sec, label)
    annotation_source: str,
) -> None:
    storage = get_storage()
    for idx, name in enumerate(channel_names):
        samples = data[idx]
        storage_key = f"studies/{study.id}/ch{idx}"
        storage.put_array(storage_key, samples)
        signal_type, confidence = guess_signal_type(name)
        db.add(
            Channel(
                study_id=study.id,
                name=name,
                signal_type=signal_type,
                mapping_confidence=confidence,
                unit=units[idx] if idx < len(units) else None,
                sampling_rate=float(fs),
                n_samples=int(samples.shape[0]),
                storage_key=storage_key,
            )
        )
    for onset_sec, duration_sec, label in annotations:
        db.add(
            Annotation(
                study_id=study.id,
                onset_sec=onset_sec,
                duration_sec=duration_sec,
                label=label,
                source=annotation_source,
            )
        )
    study.duration_sec = data.shape[1] / fs


def _ingest_edf(study: Study, upload_dir: Path, db: Session) -> None:
    edf_path = next(upload_dir.glob("*.edf") or upload_dir.glob("*.EDF"))
    raw = mne.io.read_raw_edf(edf_path, preload=True, verbose=False)
    fs = float(raw.info["sfreq"])
    data = raw.get_data()  # volts, shape (n_channels, n_samples)
    units = ["V"] * len(raw.ch_names)
    annotations = [
        (float(onset), float(duration), str(desc))
        for onset, duration, desc in zip(raw.annotations.onset, raw.annotations.duration, raw.annotations.description)
    ]
    _write_channels_and_annotations(db, study, list(raw.ch_names), units, fs, data, annotations, "edf")


def _ingest_wfdb(study: Study, record_path: Path, db: Session) -> None:
    """`record_path` has no extension — e.g. .../slp01a for slp01a.hea/.dat."""
    record = wfdb.rdrecord(str(record_path))
    data = record.p_signal.T  # (n_channels, n_samples)
    units = list(record.units) if record.units else [None] * record.n_sig
    annotations: list[tuple[float, float, str]] = []
    for ext in ("st", "atr"):
        ann_path = record_path.with_suffix(f".{ext}")
        if ann_path.exists():
            ann = wfdb.rdann(str(record_path), ext)
            annotations = [
                (float(sample) / ann.fs, 30.0, (note.strip() or "?"))
                for sample, note in zip(ann.sample, ann.aux_note)
            ]
            break
    _write_channels_and_annotations(db, study, list(record.sig_name), units, float(record.fs), data, annotations, "wfdb")


def _ingest_csv_json(study: Study, upload_dir: Path, db: Session) -> None:
    csv_path = next(upload_dir.glob("*.csv"))
    json_path = next(upload_dir.glob("*.json"))
    meta = json.loads(json_path.read_text())
    fs = float(meta["sampling_rate"])
    units_by_name: dict[str, str] = meta.get("units", {})

    with csv_path.open(newline="") as f:
        reader = csv_module.reader(f)
        header = next(reader)
        rows = [[float(x) for x in row] for row in reader if row]
    if not rows:
        raise UnsupportedUploadError("CSV upload has a header but no data rows.")

    data = np.array(rows, dtype=np.float32).T  # (n_channels, n_samples)
    channel_names = header
    units = [units_by_name.get(name) for name in channel_names]
    _write_channels_and_annotations(db, study, channel_names, units, fs, data, [], "upload")


def ingest_upload(db: Session, study_id: int) -> Study:
    study = db.get(Study, study_id)
    if study is None:
        raise ValueError(f"Study {study_id} not found")

    upload_dir = get_upload_dir(study.record_name)
    study.status = "downloading"  # reusing the same status vocabulary as public ingestion
    study.error_message = None
    db.commit()

    try:
        filenames = [p.name for p in upload_dir.iterdir()]
        fmt = detect_format(filenames)

        if fmt == "wfdb_zip":
            zip_path = next(upload_dir.glob("*.zip"))
            extract_dir = upload_dir / "_extracted"
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
            hea_path = next(extract_dir.rglob("*.hea"))
            _ingest_wfdb(study, hea_path.with_suffix(""), db)
        elif fmt == "wfdb":
            hea_path = next(upload_dir.glob("*.hea"))
            _ingest_wfdb(study, hea_path.with_suffix(""), db)
        elif fmt == "edf":
            _ingest_edf(study, upload_dir, db)
        elif fmt == "csv_json":
            _ingest_csv_json(study, upload_dir, db)

        study.status = "ingested"
        db.commit()
        db.refresh(study)
        return study
    except Exception as exc:  # noqa: BLE001 — persisted for API/UI visibility, then re-raised
        db.rollback()
        study.status = "error"
        study.error_message = str(exc)[:1024]
        db.commit()
        raise


UPLOAD_ROOT_NAME = "uploads"


def get_upload_dir(upload_id: str) -> Path:
    from app.storage import REPO_ROOT

    upload_dir = REPO_ROOT / "data" / UPLOAD_ROOT_NAME / upload_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def save_uploaded_files(upload_id: str, files: list[tuple[str, bytes]]) -> None:
    upload_dir = get_upload_dir(upload_id)
    total_bytes = sum(len(content) for _, content in files)
    if total_bytes > MAX_UPLOAD_BYTES:
        shutil.rmtree(upload_dir, ignore_errors=True)
        raise UnsupportedUploadError(f"Upload exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)}MB limit.")
    for filename, content in files:
        safe_name = Path(filename).name  # strip any path components — never trust client paths
        (upload_dir / safe_name).write_bytes(content)
