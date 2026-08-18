from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models.phenotype_label import PhenotypeLabel
from app.db.models.respiratory_event import RespiratoryEvent
from app.db.models.study import Study
from app.db.session import get_db
from app.schemas.phenotyping import ClusterOut, LabelUpdate, PhenotypeEventOut, PhenotypesOut
from app.services.fingerprint.vector import FINGERPRINT_AXES, fingerprint_vector
from app.services.phenotyping.clustering import run_kmeans
from app.services.respiratory_events.pipeline import ensure_eeg_enriched, ensure_hr_enriched

router = APIRouter(tags=["phenotyping"])


@router.get("/phenotypes", response_model=PhenotypesOut)
def get_phenotypes(k: int = Query(3, ge=2, le=8), db: Session = Depends(get_db)) -> PhenotypesOut:
    rows = (
        db.query(RespiratoryEvent, Study)
        .join(Study, RespiratoryEvent.study_id == Study.id)
        .filter(Study.status == "ingested")
        .all()
    )

    if len(rows) < k:
        return PhenotypesOut(
            available=False,
            message=f"Need at least {k} detected events across all ingested studies to form {k} "
            f"phenotypes — only {len(rows)} available. Ingest more studies or lower k.",
            k=k, axes=FINGERPRINT_AXES, clusters=[], events=[],
        )

    # Fingerprints need EEG/HR features too — enrich per study (idempotent,
    # cheap after the first run) before vectorizing.
    events_by_study: dict[int, list[RespiratoryEvent]] = {}
    for event, study in rows:
        events_by_study.setdefault(study.id, []).append(event)
    studies_by_id = {study.id: study for _, study in rows}
    for study_id, study_events in events_by_study.items():
        study = studies_by_id[study_id]
        ensure_eeg_enriched(db, study, study_events)
        ensure_hr_enriched(db, study, study_events)

    vectors = [fingerprint_vector(event) for event, _ in rows]
    assignments, clusters = run_kmeans(vectors, k)

    overrides = {
        row.cluster_index: row.label
        for row in db.query(PhenotypeLabel).filter(PhenotypeLabel.k == k).all()
    }

    cluster_out = [
        ClusterOut(cluster_index=c.cluster_index, label=overrides.get(c.cluster_index, c.default_label), size=c.size, centroid=c.centroid)
        for c in clusters
    ]
    events_out = [
        PhenotypeEventOut(
            event_id=event.id, study_id=study.id, study_label=study.display_name or study.record_name,
            onset_sec=event.onset_sec, event_type=event.event_type,
            cluster_index=assignments[i], fingerprint=vectors[i],
        )
        for i, (event, study) in enumerate(rows)
    ]

    return PhenotypesOut(available=True, message=None, k=k, axes=FINGERPRINT_AXES, clusters=cluster_out, events=events_out)


@router.patch("/phenotypes/{k}/clusters/{cluster_index}", response_model=ClusterOut)
def rename_cluster(k: int, cluster_index: int, update: LabelUpdate, db: Session = Depends(get_db)) -> ClusterOut:
    existing = (
        db.query(PhenotypeLabel)
        .filter(PhenotypeLabel.k == k, PhenotypeLabel.cluster_index == cluster_index)
        .one_or_none()
    )
    if existing is None:
        existing = PhenotypeLabel(k=k, cluster_index=cluster_index, label=update.label)
        db.add(existing)
    else:
        existing.label = update.label
    db.commit()

    # Recompute this cluster's current size/centroid so the response stays consistent.
    result = get_phenotypes(k=k, db=db)
    match = next((c for c in result.clusters if c.cluster_index == cluster_index), None)
    if match is None:
        raise HTTPException(status_code=404, detail="Cluster not found for the current data.")
    return match
