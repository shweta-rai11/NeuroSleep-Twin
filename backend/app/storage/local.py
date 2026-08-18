import shutil
from pathlib import Path

import numpy as np

from app.storage.base import ObjectStorage


class LocalObjectStorage(ObjectStorage):
    """Filesystem-backed stand-in for the S3-compatible bucket, rooted at
    data/processed/objects/ (already gitignored). Arrays are stored as
    float32 .npy — waveform precision is not needed beyond that, and it
    halves storage versus float64.
    """

    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = self.root_dir / key
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def put_array(self, key: str, array: np.ndarray) -> None:
        np.save(self._path(key).with_suffix(".npy"), array.astype(np.float32), allow_pickle=False)

    def get_array(self, key: str) -> np.ndarray:
        return np.load(self._path(key).with_suffix(".npy"), allow_pickle=False)

    def exists(self, key: str) -> bool:
        return self._path(key).with_suffix(".npy").exists()

    def delete_prefix(self, prefix: str) -> None:
        target = self.root_dir / prefix
        if target.exists():
            shutil.rmtree(target)
