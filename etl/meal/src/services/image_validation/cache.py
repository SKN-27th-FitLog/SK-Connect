from collections.abc import Callable
from typing import Any


class ImageVectorCache:
    def __init__(self, vector_provider: Callable[[str], Any]):
        self.vector_provider = vector_provider
        self._vectors: dict[str, Any] = {}
        self.hit_count = 0
        self.miss_count = 0

    def get(self, url: str) -> Any:
        key = str(url or "").strip()
        if key in self._vectors:
            self.hit_count += 1
            return self._vectors[key]

        self.miss_count += 1
        vector = self.vector_provider(key)
        self._vectors[key] = vector
        return vector
