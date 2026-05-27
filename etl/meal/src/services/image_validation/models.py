from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidatedImage:
    data: dict[str, Any]

    @classmethod
    def from_source(
        cls,
        source: dict[str, Any],
        group_id: str,
        group_order: int,
        nearest_similarity: float,
        model_version: str,
    ) -> "ValidatedImage":
        data = deepcopy(source)
        data["validation"] = {
            "status": "keep",
            "group_id": group_id,
            "group_order": group_order,
            "nearest_similarity": round(float(nearest_similarity), 6),
            "model_version": model_version,
            "alt_text": f"식당 유사 이미지 그룹 {group_id} {group_order}번",
        }
        return cls(data)


@dataclass(frozen=True)
class DroppedImage:
    data: dict[str, Any]

    @classmethod
    def from_source(
        cls,
        source: dict[str, Any],
        reason: str,
        nearest_similarity: float | None,
        model_version: str,
    ) -> "DroppedImage":
        data = deepcopy(source)
        data["validation"] = {
            "status": "drop",
            "reason": reason,
            "nearest_similarity": (
                None if nearest_similarity is None else round(float(nearest_similarity), 6)
            ),
            "model_version": model_version,
        }
        return cls(data)


@dataclass(frozen=True)
class ImageValidationDecision:
    kept_images: list[dict[str, Any]]
    dropped_images: list[dict[str, Any]]
    total_count: int
    kept_count: int
    dropped_count: int
    model_version: str

    def to_record(self) -> dict[str, Any]:
        return {
            "total_count": self.total_count,
            "kept_count": self.kept_count,
            "dropped_count": self.dropped_count,
            "model_version": self.model_version,
        }
