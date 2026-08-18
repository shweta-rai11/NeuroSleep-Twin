import shutil

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models.channel import Channel
from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.study import (
    ChannelMappingUpdate,
    ChannelOut,
    ChannelQcOut,
    IngestJobOut,
    SignalWindowOut,
    StudyListItemOut,
    StudyOut,
    StudyQcOut,
)
from app.services.channel_mapping import STANDARD_SIGNAL_TYPES
from app.services.qc.signal_qc import compute_channel_qc
from app.services.signal_window import downsample_minmax
from app.storage import get_storage
from app.worker.celery_app import celery_app
from app.worker.tasks.ingestion import ingest_mitbih_record_task

router = APIRouter(tags=["studies"])


@router.post("/datasets/{dataset_id}/records/{record_name}/ingest", response_model=IngestJobOut)
def ingest_record(dataset_id: str, record_name: str) -> IngestJobOut:
    if dataset_id != "mitbih-psg":
        raise HTTPException(status_code=404, detail=f"Unknown dataset '{dataset_id}'")
    task = ingest_mitbih_record_task.delay(record_name)
    return IngestJobOut(task_id=task.id, status="queued")


@router.get("/ingest-jobs/{task_id}", response_model=IngestJobOut)
def get_ingest_job(task_id: str) -> IngestJobOut:
    result = celery_app.AsyncResult(task_id)
    if result.failed():
        return IngestJobOut(task_id=task_id, status="error", error=str(result.result))
    if result.successful():
        payload = result.result
        return IngestJobOut(task_id=task_id, status="ready", study_id=payload["study_id"])
    return IngestJobOut(task_id=task_id, status=result.status.lower())


@router.get("/studies", response_model=list[StudyListItemOut])
def list_studies(db: Session = Depends(get_db)) -> list[Study]:
    return db.query(Study).order_by(Study.created_at.desc()).all()


@router.get("/studies/{study_id}", response_model=StudyOut)
def get_study(study_id: int, db: Session = Depends(get_db)) -> Study:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    return study


@router.get("/channel-types")
def list_channel_types() -> list[str]:
    return STANDARD_SIGNAL_TYPES


@router.patch("/studies/{study_id}/channels/{channel_id}", response_model=ChannelOut)
def update_channel_mapping(
    study_id: int, channel_id: int, update: ChannelMappingUpdate, db: Session = Depends(get_db)
) -> Channel:
    channel = db.get(Channel, channel_id)
    if channel is None or channel.study_id != study_id:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found on study {study_id}")
    if update.signal_type is not None and update.signal_type not in STANDARD_SIGNAL_TYPES:
        raise HTTPException(status_code=400, detail=f"'{update.signal_type}' is not a standard signal type")

    channel.signal_type = update.signal_type
    channel.mapping_confidence = 1.0  # a human confirmed it — no longer just a guess
    channel.mapping_confirmed = True
    db.commit()
    db.refresh(channel)
    return channel


@router.post("/studies/{study_id}/confirm-mapping", response_model=StudyOut)
def confirm_channel_mapping(study_id: int, db: Session = Depends(get_db)) -> Study:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    for channel in study.channels:
        channel.mapping_confirmed = True
    study.channel_mapping_confirmed = True
    db.commit()
    db.refresh(study)
    return study


@router.get("/studies/{study_id}/qc", response_model=StudyQcOut)
def get_study_qc(study_id: int, db: Session = Depends(get_db)) -> StudyQcOut:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")

    storage = get_storage()
    results = [
        compute_channel_qc(ch.id, ch.name, ch.signal_type, storage.get_array(ch.storage_key), ch.sampling_rate)
        for ch in study.channels
    ]
    overall_score = round(sum(r.score for r in results) / len(results), 1) if results else 0.0
    overall_label = (
        "Excellent" if overall_score >= 85 else "Good" if overall_score >= 70 else "Fair" if overall_score >= 50 else "Poor"
    )
    return StudyQcOut(
        study_id=study_id,
        overall_score=overall_score,
        overall_label=overall_label,
        channels=[ChannelQcOut(**vars(r)) for r in results],
    )


@router.delete("/studies/{study_id}", status_code=204)
def delete_study(study_id: int, db: Session = Depends(get_db)) -> None:
    """Deletes the study, its channel waveforms, and (for uploads) the
    original uploaded files — users can remove their data at any time
    (README §11)."""
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")

    get_storage().delete_prefix(f"studies/{study_id}")
    if study.source == "upload":
        from app.services.ingestion.upload import get_upload_dir

        shutil.rmtree(get_upload_dir(study.record_name), ignore_errors=True)

    db.delete(study)
    db.commit()


@router.get("/studies/{study_id}/channels/{channel_id}/signal", response_model=SignalWindowOut)
def get_signal_window(
    study_id: int,
    channel_id: int,
    start_sec: float = Query(0, ge=0),
    end_sec: float = Query(...),
    max_points: int = Query(2000, ge=10, le=20000),
    db: Session = Depends(get_db),
) -> SignalWindowOut:
    channel = db.get(Channel, channel_id)
    if channel is None or channel.study_id != study_id:
        raise HTTPException(status_code=404, detail=f"Channel {channel_id} not found on study {study_id}")
    if end_sec <= start_sec:
        raise HTTPException(status_code=400, detail="end_sec must be greater than start_sec")

    samples = get_storage().get_array(channel.storage_key)
    fs = channel.sampling_rate

    start_idx = max(0, int(start_sec * fs))
    end_idx = min(len(samples), int(end_sec * fs))
    if start_idx >= end_idx:
        return SignalWindowOut(
            channel_id=channel_id, start_sec=start_sec, end_sec=end_sec,
            sampling_rate=fs, point_interval_sec=1 / fs, t=[], v=[],
        )

    window_v = samples[start_idx:end_idx]
    window_t = start_idx / fs + np.arange(len(window_v)) / fs

    raw_point_interval = 1 / fs
    out_t, out_v = downsample_minmax(window_t, window_v, max_points)
    point_interval = raw_point_interval if len(out_t) == len(window_t) else (end_sec - start_sec) / max_points

    return SignalWindowOut(
        channel_id=channel_id,
        start_sec=start_sec,
        end_sec=end_sec,
        sampling_rate=fs,
        point_interval_sec=point_interval,
        t=out_t.tolist(),
        v=out_v.tolist(),
    )
