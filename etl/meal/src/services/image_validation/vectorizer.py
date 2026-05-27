from abc import ABC, abstractmethod
from io import BytesIO
from typing import Any
import urllib.request

import numpy as np
from PIL import Image

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None


class MissingImageVectorizerDependency(RuntimeError):
    pass


def normalize_vector(vector: Any) -> np.ndarray:
    arr = np.asarray(vector, dtype=float).reshape(-1)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


class ImageVectorizer(ABC):
    model_version: str

    @abstractmethod
    def vectorize(self, url: str) -> np.ndarray:
        raise NotImplementedError


class ClipImageVectorizer(ImageVectorizer):
    def __init__(
        self,
        model_name: str = "clip-ViT-B-32",
        request_timeout_seconds: int = 15,
    ):
        if SentenceTransformer is None:
            raise MissingImageVectorizerDependency(
                "sentence-transformers is required for ClipImageVectorizer"
            )
        self.model_name = model_name
        self.model_version = model_name
        self.request_timeout_seconds = request_timeout_seconds
        self.model = SentenceTransformer(model_name)

    def vectorize(self, url: str) -> np.ndarray:
        image = self._load_image(url)
        return normalize_vector(self.model.encode([image], convert_to_numpy=True)[0])

    def _load_image(self, url: str) -> Image.Image:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
            image_bytes = response.read()
        return Image.open(BytesIO(image_bytes)).convert("RGB")
