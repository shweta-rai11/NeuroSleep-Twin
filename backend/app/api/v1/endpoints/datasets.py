import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

# data/datasets/registry/ lives at the repo root, two levels above backend/app
REGISTRY_DIR = Path(__file__).resolve().parents[5] / "data" / "datasets" / "registry"

router = APIRouter(prefix="/datasets", tags=["datasets"])


def _load_registry() -> list[dict]:
    if not REGISTRY_DIR.exists():
        return []
    entries = []
    for path in sorted(REGISTRY_DIR.glob("*.json")):
        with path.open() as f:
            entries.append(json.load(f))
    return entries


@router.get("")
def list_datasets() -> list[dict]:
    """Public dataset catalog. Each entry's provenance fields (source, license,
    citation, version) come from the official source — see data/datasets/registry/.
    """
    return _load_registry()


@router.get("/{dataset_id}")
def get_dataset(dataset_id: str) -> dict:
    for entry in _load_registry():
        if entry.get("id") == dataset_id:
            return entry
    raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found in registry")
