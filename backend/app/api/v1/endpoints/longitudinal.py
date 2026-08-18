from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.longitudinal import LongitudinalOut, NightSummaryOut, PatientGroupOut
from app.services.longitudinal.patient_grouping import patient_key
from app.services.oxygen_burden.analysis import clean_spo2, compute_oxygen_summary
from app.services.respiratory_events.pipeline import get_or_detect_events, pick_spo2_channel
from app.services.sleep_staging.from_annotations import parse_hypnogram
from app.storage import get_storage

router = APIRouter(tags=["longitudinal"])


def _build_night_summary(db: Session, study: Study) -> NightSummaryOut:
    duration_hr = (study.duration_sec or 0) / 3600
    _, events = get_or_detect_events(db, study)
    events_per_hour = round(len(events) / duration_hr, 2) if duration_hr > 0 else None

    mean_spo2 = odi = None
    spo2_channel = pick_spo2_channel(study.channels)
    if spo2_channel is not None:
        samples, artifact_pct = clean_spo2(get_storage().get_array(spo2_channel.storage_key))
        summary = compute_oxygen_summary(samples, spo2_channel.sampling_rate, artifact_pct)
        mean_spo2, odi = summary.mean_spo2, summary.odi

    epochs = parse_hypnogram(study.annotations)
    stage_minutes: dict[str, float] = {}
    for e in epochs:
        stage_minutes[e.stage] = stage_minutes.get(e.stage, 0.0) + e.duration_sec / 60
    total_minutes = sum(stage_minutes.values())
    stage_pct = {k: round(v / total_minutes * 100, 1) for k, v in stage_minutes.items()} if total_minutes > 0 else {}

    return NightSummaryOut(
        study_id=study.id, record_name=study.record_name, duration_sec=study.duration_sec or 0,
        events_per_hour=events_per_hour, mean_spo2=mean_spo2, odi=odi, stage_pct=stage_pct,
    )


@router.get("/longitudinal", response_model=LongitudinalOut)
def get_longitudinal(db: Session = Depends(get_db)) -> LongitudinalOut:
    studies = db.query(Study).filter(Study.status == "ingested").all()

    groups: dict[str, list[Study]] = {}
    for study in studies:
        key = patient_key(study.dataset_id, study.record_name)
        groups.setdefault(key, []).append(study)

    multi_night = {k: v for k, v in groups.items() if len(v) >= 2}
    if not multi_night:
        return LongitudinalOut(
            available=False,
            message="No two ingested recordings are identified as the same person's multiple "
            "nights yet — MIT-BIH PSG's slpNNa/slpNNb pairs are the only ones this app can "
            "confidently group (e.g. ingest both slp01a and slp01b).",
            patients=[],
        )

    patients = [
        PatientGroupOut(
            patient_key=key,
            nights=sorted((_build_night_summary(db, s) for s in group), key=lambda n: n.record_name),
        )
        for key, group in multi_night.items()
    ]
    return LongitudinalOut(available=True, message=None, patients=patients)
