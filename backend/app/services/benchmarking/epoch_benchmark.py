"""Benchmarks the candidate respiratory-event detector against a study's own
ground-truth annotations (README §6, §20 — patient-level, no invented
numbers, "No benchmark available" rather than a fabricated metric).

MIT-BIH PSG's '.st' file flags respiratory events per 30-second epoch, not
with precise onset/offset times, so evaluation is necessarily epoch-level:
did our detector place a candidate event inside an epoch the human scorer
flagged as apnea/hypopnea? Ground-truth codes are sourced directly from
PhysioNet's slpdb documentation (README.st) — not guessed:
  H=hypopnea, HA=hypopnea+arousal, OA=obstructive apnea,
  X=obstructive apnea+arousal, CA=central apnea, CAA=central apnea+arousal.
L/LA (leg movements) and A/MT (arousal/movement-time) are NOT respiratory
events and must not be counted as such.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve

from app.db.models.annotation import Annotation
from app.db.models.respiratory_event import RespiratoryEvent

RESPIRATORY_EVENT_CODES = {"H", "HA", "OA", "X", "CA", "CAA"}


@dataclass
class EpochBenchmark:
    n_epochs: int
    n_positive_epochs: int
    tp: int
    fp: int
    fn: int
    tn: int
    sensitivity: float | None
    specificity: float | None
    precision: float | None
    auroc: float | None
    auprc: float | None
    roc_fpr: list[float]
    roc_tpr: list[float]
    pr_precision: list[float]
    pr_recall: list[float]
    calibration_predicted: list[float]
    calibration_observed: list[float]


def _epoch_ground_truth(annotation: Annotation) -> bool:
    tokens = annotation.label.strip().split(" ")[1:]  # first token is the sleep stage
    return any(t in RESPIRATORY_EVENT_CODES for t in tokens)


def _epoch_score(onset_sec: float, duration_sec: float, events: list[RespiratoryEvent]) -> float:
    """Max severity (1 - depth_ratio) among detected events overlapping this epoch, else 0."""
    epoch_end = onset_sec + duration_sec
    overlapping = [e for e in events if e.onset_sec < epoch_end and e.onset_sec + e.duration_sec > onset_sec]
    if not overlapping:
        return 0.0
    return max(1 - e.depth_ratio for e in overlapping)


def compute_epoch_benchmark(annotations: list[Annotation], events: list[RespiratoryEvent]) -> EpochBenchmark | None:
    epochs = [a for a in annotations if a.source == "st"]
    if not epochs:
        return None

    y_true = np.array([1 if _epoch_ground_truth(a) else 0 for a in epochs])
    y_score = np.array([_epoch_score(a.onset_sec, a.duration_sec, events) for a in epochs])
    y_pred = (y_score > 0).astype(int)

    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))

    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else None
    specificity = tn / (tn + fp) if (tn + fp) > 0 else None
    precision = tp / (tp + fp) if (tp + fp) > 0 else None

    has_both_classes = 0 < y_true.sum() < len(y_true)
    auroc = auprc = None
    roc_fpr = roc_tpr = pr_precision = pr_recall = []
    calibration_predicted = calibration_observed = []

    if has_both_classes:
        auroc = round(float(roc_auc_score(y_true, y_score)), 4)
        auprc = round(float(average_precision_score(y_true, y_score)), 4)
        fpr, tpr, _ = roc_curve(y_true, y_score)
        roc_fpr, roc_tpr = fpr.round(4).tolist(), tpr.round(4).tolist()
        prec, rec, _ = precision_recall_curve(y_true, y_score)
        pr_precision, pr_recall = prec.round(4).tolist(), rec.round(4).tolist()

        n_bins = min(8, int(np.sum(y_score > 0)) or 1)
        if n_bins >= 2:
            bin_edges = np.linspace(0, 1, n_bins + 1)
            bin_idx = np.clip(np.digitize(y_score, bin_edges) - 1, 0, n_bins - 1)
            for b in range(n_bins):
                mask = bin_idx == b
                if mask.sum() == 0:
                    continue
                calibration_predicted.append(round(float(y_score[mask].mean()), 4))
                calibration_observed.append(round(float(y_true[mask].mean()), 4))

    return EpochBenchmark(
        n_epochs=len(epochs), n_positive_epochs=int(y_true.sum()),
        tp=tp, fp=fp, fn=fn, tn=tn,
        sensitivity=round(sensitivity, 4) if sensitivity is not None else None,
        specificity=round(specificity, 4) if specificity is not None else None,
        precision=round(precision, 4) if precision is not None else None,
        auroc=auroc, auprc=auprc,
        roc_fpr=roc_fpr, roc_tpr=roc_tpr, pr_precision=pr_precision, pr_recall=pr_recall,
        calibration_predicted=calibration_predicted, calibration_observed=calibration_observed,
    )
