from pydantic import BaseModel


class ConfusionMatrixOut(BaseModel):
    tp: int
    fp: int
    fn: int
    tn: int


class CurveOut(BaseModel):
    x: list[float]
    y: list[float]


class BenchmarkOut(BaseModel):
    study_id: int
    available: bool
    message: str | None
    n_epochs: int
    n_positive_epochs: int
    confusion: ConfusionMatrixOut | None
    sensitivity: float | None
    specificity: float | None
    precision: float | None
    auroc: float | None
    auprc: float | None
    roc_curve: CurveOut | None
    pr_curve: CurveOut | None
    calibration_predicted: list[float]
    calibration_observed: list[float]
