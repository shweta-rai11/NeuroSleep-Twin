"""Assembles the ONLY thing the Research Assistant (Phase 15) ever sees: a
JSON-safe snapshot of already-computed pipeline output. It never receives
raw signals and never reasons over them directly — every number here was
produced by an earlier, disclosed pipeline stage (README §5, §22)."""

from sqlalchemy.orm import Session

from app.db.models.study import Study
from app.services.benchmarking.epoch_benchmark import compute_epoch_benchmark
from app.services.oxygen_burden.analysis import clean_spo2, compute_oxygen_summary
from app.services.respiratory_events.pipeline import get_or_detect_events, pick_spo2_channel
from app.services.sleep_staging.from_annotations import parse_hypnogram
from app.storage import get_storage


def build_study_context(db: Session, study: Study) -> dict:
    duration_hr = (study.duration_sec or 0) / 3600
    context: dict = {
        "study": {
            "record_name": study.record_name,
            "display_name": study.display_name,
            "source": study.source,
            "duration_minutes": round((study.duration_sec or 0) / 60, 1),
            "channels": [{"name": c.name, "signal_type": c.signal_type} for c in study.channels],
        }
    }

    _, events = get_or_detect_events(db, study)
    if events:
        apnea = sum(1 for e in events if e.event_type == "apnea")
        context["respiratory_events"] = {
            "total": len(events), "apnea": apnea, "hypopnea": len(events) - apnea,
            "events_per_hour": round(len(events) / duration_hr, 2) if duration_hr > 0 else None,
        }

    spo2_channel = pick_spo2_channel(study.channels)
    if spo2_channel is not None:
        samples, artifact_pct = clean_spo2(get_storage().get_array(spo2_channel.storage_key))
        summary = compute_oxygen_summary(samples, spo2_channel.sampling_rate, artifact_pct)
        context["oxygen_burden"] = {
            "mean_spo2": summary.mean_spo2, "min_spo2": summary.min_spo2,
            "pct_time_below_90": summary.pct_time_below_90, "odi": summary.odi,
        }

    epochs = parse_hypnogram(study.annotations)
    if epochs:
        stage_minutes: dict[str, float] = {}
        for e in epochs:
            stage_minutes[e.stage] = stage_minutes.get(e.stage, 0.0) + e.duration_sec / 60
        # Keys spell out the unit explicitly — a smaller local model narrating
        # this JSON has, in testing, misread a bare "sleep_stages" dict of
        # minutes as percentages. Self-documenting keys fixed it.
        context["sleep_stage_minutes"] = {k: round(v, 1) for k, v in stage_minutes.items()}

    benchmark = compute_epoch_benchmark(study.annotations, events)
    if benchmark is not None:
        context["benchmark_vs_ground_truth"] = {
            "sensitivity": benchmark.sensitivity, "specificity": benchmark.specificity,
            "precision": benchmark.precision, "auroc": benchmark.auroc,
        }

    return context
