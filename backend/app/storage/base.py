from abc import ABC, abstractmethod

import numpy as np


class ObjectStorage(ABC):
    """S3-compatible object storage interface. `LocalObjectStorage` is the
    filesystem-backed implementation used until infra (Phase 18) stands up
    a real S3-compatible endpoint (see README §3, §11) — swap the factory in
    __init__.py without touching callers.
    """

    @abstractmethod
    def put_array(self, key: str, array: np.ndarray) -> None: ...

    @abstractmethod
    def get_array(self, key: str) -> np.ndarray: ...

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete_prefix(self, prefix: str) -> None: ...
