"""Ingests a single MIT-BIH Polysomnographic Database record from PhysioNet.

This is intentionally the minimal real pipeline for Phase 2 + the Phase 6
viewer: download the record + its sleep-stage/apnea annotation file, store
raw per-channel waveforms in object storage, and record metadata/annotations
in Postgres. It does not interpret or score anything — that is later phases'
job (sleep staging, respiratory event detection, ...). Annotations are kept
as the dataset's own raw epoch codes (see README §5, §6 — no invented
numbers, no silent reinterpretation of source data).
"""

import logging

import wfdb
from sqlalchemy.orm import Session

from app.db.models.annotation import Annotation
from app.db.models.channel import Channel
from app.db.models.study import Study
from app.services.channel_mapping import guess_signal_type
from app.storage import get_storage

logger = logging.getLogger(__name__)

DATASET_ID = "mitbih-psg"
PN_DIR = "slpdb/1.0.0"

# MIT-BIH PSG '.st' annotations are recorded once per 30s epoch (PhysioNet
# slpdb documentation) — not encoded in the annotation file itself.
ST_EPOCH_SEC = 30.0


def get_or_create_study(db: Session, record_name: str) -> Study:
    existing = (
        db.query(Study)
        .filter(Study.dataset_id == DATASET_ID, Study.record_name == record_name)
        .one_or_none()
    )
    if existing is not None:
        return existing
    study = Study(dataset_id=DATASET_ID, record_name=record_name, status="pending")
    db.add(study)
    db.commit()
    db.refresh(study)
    return study


def ingest_record(db: Session, record_name: str) -> Study:
    """Idempotent: if the record is already ingested, returns it as-is
    without re-downloading."""
    study = get_or_create_study(db, record_name)
    if study.status == "ingested":
        return study

    study.status = "downloading"
    study.error_message = None
    db.commit()

    try:
        record = wfdb.rdrecord(record_name, pn_dir=PN_DIR)
        storage = get_storage()

        # Clear any partial channels from a previous failed attempt before re-writing.
        for existing_channel in list(study.channels):
            db.delete(existing_channel)
        db.flush()

        for idx, name in enumerate(record.sig_name):
            samples = record.p_signal[:, idx]
            storage_key = f"studies/{study.id}/ch{idx}"
            storage.put_array(storage_key, samples)
            signal_type, confidence = guess_signal_type(name)
            db.add(
                Channel(
                    study_id=study.id,
                    name=name,
                    signal_type=signal_type,
                    mapping_confidence=confidence,
                    unit=record.units[idx] if idx < len(record.units) else None,
                    sampling_rate=float(record.fs),
                    n_samples=int(record.sig_len),
                    storage_key=storage_key,
                )
            )

        try:
            ann = wfdb.rdann(record_name, "st", pn_dir=PN_DIR)
            for sample, aux_note in zip(ann.sample, ann.aux_note):
                label = aux_note.strip() or "?"
                db.add(
                    Annotation(
                        study_id=study.id,
                        onset_sec=float(sample) / ann.fs,
                        duration_sec=ST_EPOCH_SEC,
                        label=label,
                        source="st",
                    )
                )
        except FileNotFoundError:
            logger.warning("No .st annotation file for record %s", record_name)

        study.duration_sec = record.sig_len / record.fs
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
