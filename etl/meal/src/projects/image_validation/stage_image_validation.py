from copy import deepcopy
from typing import Any, Callable

from src.core.base_stage import BaseStage
from src.services.image_validation.grouping import (
    DEFAULT_IMAGE_SIMILARITY_THRESHOLD,
    DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE,
    group_similar_images,
)
from src.services.image_validation.menu_alt import enrich_images_with_review_menu_alt


class StageImageValidation(BaseStage):
    NAME = "image_validation"

    def __init__(
        self,
        vector_provider: Callable[[str], Any],
        similarity_threshold: float = DEFAULT_IMAGE_SIMILARITY_THRESHOLD,
        min_group_size: int = DEFAULT_MIN_SIMILAR_IMAGE_GROUP_SIZE,
        model_version: str = "unknown",
    ):
        super().__init__(self.NAME)
        self.vector_provider = vector_provider
        self.similarity_threshold = similarity_threshold
        self.min_group_size = min_group_size
        self.model_version = model_version

    def execute(
        self,
        records: list[dict[str, Any]],
        batch_id: str,
        category_cd: str,
        run_attempt: int = 1,
    ) -> list[dict[str, Any]]:
        if not isinstance(records, list):
            raise ValueError("StageImageValidation input must be a list of records.")

        validated_records: list[dict[str, Any]] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("StageImageValidation record must be a dictionary.")
            validated_records.append(
                self._validate_record(
                    record,
                    batch_id=batch_id,
                    category_cd=category_cd,
                    run_attempt=run_attempt,
                )
            )
        return validated_records

    def _validate_record(
        self,
        record: dict[str, Any],
        batch_id: str,
        category_cd: str,
        run_attempt: int,
    ) -> dict[str, Any]:
        output = deepcopy(record)
        images = record.get("images", [])
        if not isinstance(images, list):
            images = []

        decision = group_similar_images(
            images=images,
            vector_provider=self.vector_provider,
            similarity_threshold=self.similarity_threshold,
            min_group_size=self.min_group_size,
            model_version=self.model_version,
        )

        output.setdefault("batch_id", batch_id)
        output.setdefault("category_cd", category_cd)
        output.setdefault("run_attempt", run_attempt)
        output["stage"] = self.NAME
        output["images"] = enrich_images_with_review_menu_alt(
            decision.kept_images,
            record.get("reviews", []),
        )
        output["dropped_images"] = decision.dropped_images
        output["image_validation"] = decision.to_record()
        return output
