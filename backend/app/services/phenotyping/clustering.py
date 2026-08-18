"""Unsupervised clustering of event fingerprints into descriptive phenotype
groups (README §12/§19) — K-means with a fixed random seed for
reproducibility. Cluster indices are stable for a given k and event set, but
NOT meaningful across different k — always re-derive default labels rather
than assuming index continuity.
"""

from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans

from app.services.fingerprint.vector import FINGERPRINT_AXES

RANDOM_STATE = 42

_TRAIT_LABELS = {
    "severity": "high severity",
    "duration": "long duration",
    "desaturation": "deep desaturation",
    "hr_response": "strong HR response",
    "arousal": "high arousal",
}


def default_cluster_label(centroid: list[float]) -> str:
    mean = float(np.mean(centroid))
    magnitude = "Mild" if mean < 0.3 else "Moderate" if mean < 0.6 else "Marked"
    dominant_idx = int(np.argmax(centroid))
    trait = _TRAIT_LABELS[FINGERPRINT_AXES[dominant_idx]]
    return f"{magnitude} — {trait}"


@dataclass
class ClusterResult:
    cluster_index: int
    size: int
    centroid: list[float]
    default_label: str


def run_kmeans(vectors: list[list[float]], k: int) -> tuple[list[int], list[ClusterResult]]:
    X = np.array(vectors)
    model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10)
    assignments = model.fit_predict(X).tolist()

    clusters = []
    for cluster_index in range(k):
        members = X[[a == cluster_index for a in assignments]]
        centroid = members.mean(axis=0).round(4).tolist() if len(members) else [0.0] * X.shape[1]
        clusters.append(
            ClusterResult(
                cluster_index=cluster_index,
                size=int(len(members)),
                centroid=centroid,
                default_label=default_cluster_label(centroid),
            )
        )
    return assignments, clusters
