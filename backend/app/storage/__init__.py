from functools import lru_cache
from pathlib import Path

from app.storage.base import ObjectStorage
from app.storage.local import LocalObjectStorage

# Repo root is four levels above this file (app/storage/__init__.py -> app -> backend -> repo root)
REPO_ROOT = Path(__file__).resolve().parents[3]


@lru_cache
def get_storage() -> ObjectStorage:
    return LocalObjectStorage(REPO_ROOT / "data" / "processed" / "objects")
