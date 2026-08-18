from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.analysis import (
    ChannelRef,
    EventFeatureResultOut,
    OxygenBurdenOut,
    OxygenSummaryOut,
    RespiratoryEventsOut,
    RespiratoryEventSummary,
    SleepStagesOut,
    StageEpochOut,
)
from app.schemas.benchmarking import BenchmarkOut, ConfusionMatrixOut, CurveOut
from app.services.benchmarking.epoch_benchmark import compute_epoch_benchmark
from app.services.oxygen_burden.analysis import clean_spo2, compute_oxygen_summary
from app.services.respiratory_events.detector import ALGORITHM_VERSION
from app.services.respiratory_events.pipeline import (
    ensure_eeg_enriched,
    ensure_hr_enriched,
    get_or_detect_events,
    pick_spo2_channel,
)
from app.services.sleep_staging.from_annotations import parse_hypnogram
from app.storage import get_storage

router = APIRouter(tags=["analysis"])


def _get_study_or_404(study_id: int, db: Session) -> Study:
    study = db.get(Study, study_id)
    if study is None:
        raise HTTPException(status_code=404, detail=f"Study {study_id} not found")
    return study


@router.get("/studies/{study_id}/respiratory-events", response_model=RespiratoryEventsOut)
def get_respiratory_events(study_id: int, db: Session = Depends(get_db)) -> RespiratoryEventsOut:
    study = _get_study_or_404(study_id, db)
    channel, events = get_or_detect_events(db, study)

    if channel is None:
        return RespiratoryEventsOut(
            study_id=study_id, available=False,
            message="No respiratory-effort/airflow channel is mapped for this study — "
            "confirm channel mapping first if one should be available.",
            channel_used=None, algorithm_version=None, summary=None, events=[],
        )

    # Best-effort: also attach EEG/HR features so each event carries a full
    # fingerprint (Phase 11) without a separate round trip. Silently skipped
    # if the study has no EEG/ECG channel — oxygen/respiratory fields alone
    # are still useful.
    ensure_eeg_enriched(db, study, events)
    ensure_hr_enriched(db, study, events)

    duration_hr = (study.duration_sec or 0) / 3600
    apnea_count = sum(1 for e in events if e.event_type == "apnea")
    hypopnea_count = len(events) - apnea_count
    summary = RespiratoryEventSummary(
        count=len(events), apnea_count=apnea_count, hypopnea_count=hypopnea_count,
        events_per_hour=round(len(events) / duration_hr, 2) if duration_hr > 0 else 0.0,
    )
    return RespiratoryEventsOut(
        study_id=study_id, available=True, message=None,
        channel_used=ChannelRef(id=channel.id, name=channel.name),
        algorithm_version=ALGORITHM_VERSION, summary=summary, events=events,
    )


@router.get("/studies/{study_id}/oxygen-burden", response_model=OxygenBurdenOut)
def get_oxygen_burden(study_id: int, db: Session = Depends(get_db)) -> OxygenBurdenOut:
    study = _get_study_or_404(study_id, db)
    spo2_channel = pick_spo2_channel(study.channels)

    if spo2_channel is None:
        return OxygenBurdenOut(
            study_id=study_id, available=False,
            message="No SpO2 channel is mapped for this study — oxygen burden needs pulse "
            "oximetry data, which this recording either lacks or hasn't been mapped yet.",
            channel_used=None, summary=None, events=[],
        )

    spo2_samples, artifact_pct = clean_spo2(get_storage().get_array(spo2_channel.storage_key))
    summary = compute_oxygen_summary(spo2_samples, spo2_channel.sampling_rate, artifact_pct)
    _, events = get_or_detect_events(db, study)

    return OxygenBurdenOut(
        study_id=study_id, available=True, message=None,
        channel_used=ChannelRef(id=spo2_channel.id, name=spo2_channel.name),
        summary=OxygenSummaryOut(**vars(summary)), events=events,
    )


@router.get("/studies/{study_id}/brain-response", response_model=EventFeatureResultOut)
def get_brain_response(study_id: int, db: Session = Depends(get_db)) -> EventFeatureResultOut:
    study = _get_study_or_404(study_id, db)
    _, events = get_or_detect_events(db, study)
    channel = ensure_eeg_enriched(db, study, events)

    if channel is None:
        return EventFeatureResultOut(
            study_id=study_id, available=False,
            message="No EEG channel is mapped for this study.", channel_used=None, events=[],
        )
    if not events:
        return EventFeatureResultOut(
            study_id=study_id, available=False,
            message="No candidate respiratory events to center a brain-response window on.",
            channel_used=ChannelRef(id=channel.id, name=channel.name), events=[],
        )
    return EventFeatureResultOut(
        study_id=study_id, available=True, message=None,
        channel_used=ChannelRef(id=channel.id, name=channel.name), events=events,
    )


@router.get("/studies/{study_id}/autonomic-response", response_model=EventFeatureResultOut)
def get_autonomic_response(study_id: int, db: Session = Depends(get_db)) -> EventFeatureResultOut:
    study = _get_study_or_404(study_id, db)
    _, events = get_or_detect_events(db, study)
    channel = ensure_hr_enriched(db, study, events)

    if channel is None:
        return EventFeatureResultOut(
            study_id=study_id, available=False,
            message="No ECG channel is mapped for this study.", channel_used=None, events=[],
        )
    if not events:
        return EventFeatureResultOut(
            study_id=study_id, available=False,
            message="No candidate respiratory events to center an autonomic-response window on.",
            channel_used=ChannelRef(id=channel.id, name=channel.name), events=[],
        )
    return EventFeatureResultOut(
        study_id=study_id, available=True, message=None,
        channel_used=ChannelRef(id=channel.id, name=channel.name), events=events,
    )


@router.get("/studies/{study_id}/benchmark", response_model=BenchmarkOut)
def get_benchmark(study_id: int, db: Session = Depends(get_db)) -> BenchmarkOut:
    study = _get_study_or_404(study_id, db)
    _, events = get_or_detect_events(db, study)
    result = compute_epoch_benchmark(study.annotations, events)

    if result is None:
        return BenchmarkOut(
            study_id=study_id, available=False,
            message="No ground-truth annotations for this study — no benchmark available.",
            n_epochs=0, n_positive_epochs=0, confusion=None,
            sensitivity=None, specificity=None, precision=None, auroc=None, auprc=None,
            roc_curve=None, pr_curve=None, calibration_predicted=[], calibration_observed=[],
        )

    message = None
    if result.auroc is None:
        message = (
            "Every epoch fell on one side of ground truth (all positive or all negative) — "
            "AUROC/AUPRC aren't defined without both classes present."
        )

    return BenchmarkOut(
        study_id=study_id, available=True, message=message,
        n_epochs=result.n_epochs, n_positive_epochs=result.n_positive_epochs,
        confusion=ConfusionMatrixOut(tp=result.tp, fp=result.fp, fn=result.fn, tn=result.tn),
        sensitivity=result.sensitivity, specificity=result.specificity, precision=result.precision,
        auroc=result.auroc, auprc=result.auprc,
        roc_curve=CurveOut(x=result.roc_fpr, y=result.roc_tpr) if result.roc_fpr else None,
        pr_curve=CurveOut(x=result.pr_recall, y=result.pr_precision) if result.pr_recall else None,
        calibration_predicted=result.calibration_predicted, calibration_observed=result.calibration_observed,
    )


@router.get("/studies/{study_id}/sleep-stages", response_model=SleepStagesOut)
def get_sleep_stages(study_id: int, db: Session = Depends(get_db)) -> SleepStagesOut:
    study = _get_study_or_404(study_id, db)
    epochs = parse_hypnogram(study.annotations)

    if not epochs:
        return SleepStagesOut(
            study_id=study_id, available=False,
            message="No ground-truth sleep-stage annotations were found for this study, and "
            "there is no automated EEG-based stager yet.",
            epochs=[], stage_minutes={},
        )

    stage_minutes: dict[str, float] = {}
    for e in epochs:
        stage_minutes[e.stage] = stage_minutes.get(e.stage, 0.0) + e.duration_sec / 60

    return SleepStagesOut(
        study_id=study_id, available=True, message=None,
        epochs=[StageEpochOut(onset_sec=e.onset_sec, duration_sec=e.duration_sec, stage=e.stage) for e in epochs],
        stage_minutes={k: round(v, 1) for k, v in stage_minutes.items()},
    )
