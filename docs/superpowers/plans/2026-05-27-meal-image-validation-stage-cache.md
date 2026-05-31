# Meal Image Validation Stage And Cache Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated meal image validation stage that validates images per restaurant before DB save, uses a run-scoped vector cache, enriches validated image alt text from exact review-image menu matches when available, and passes only validated food images to Stage4.

**Architecture:** Add a new `image_validation` project between `ProcessService` and `SaveService`. The new stage reads Stage3 normalized JSONL, compares images only within each restaurant record, writes validated JSONL under the existing `process=cleaning` partition, and leaves Stage4 responsible only for DB insertion and HTML tag creation. The cache is handler/run scoped to comply with the current design rule that allows execution-scope cache and forbids global cache.

**Tech Stack:** Python 3.14 virtualenv, pytest, existing `HivePathBuilder`/`JsonlWriter`, `numpy`, `Pillow`, `sentence-transformers` for CLIP-compatible image embeddings behind an adapter interface, fake vectorizers in tests.

---

## Project Analysis

Current flow:

```text
CrawlService
 -> ProcessService
    -> Stage2CandidateParsing
    -> Stage3ValidationNormalization
 -> RecipeService
 -> SaveService
    -> Stage4Load
```

Relevant current contracts:

- `Stage3ValidationNormalization` writes normalized records containing `images`.
- `SaveService` currently reads `validation_normalization_*.jsonl`.
- `Stage4Load` inserts `record["images"]` into DB through `_load_images`.
- `images.image_url` stores an HTML `<img ...>` tag, not a raw URL.
- Validated duplicate/similar image groups must remain in `validation.group_id` and `validation.group_order`; the final `<img alt="...">` should prefer menu names when they can be resolved.
- Similar image groups must require at least 3 images by default, and each kept image must have at least 2 direct similar peers in the same restaurant group. Connected-chain-only groups are not enough.
- When one unambiguous `ordered_menus` set is found by exact `review_images` URL match inside a similar image group, propagate that menu name set to every image in the group and set `validation.alt_text` to the menu names only. If the group has conflicting menu sets, only directly matched images receive their own menu-name alt text. Do not use nickname-only matching in this implementation.
- `Folder_Structure_Report.md` says stage files do data processing, services orchestrate stage I/O, and file prefixes distinguish stages inside shared partitions.
- `Design.MD` allows handler/run-scoped cache but forbids global cache. This plan implements run-scoped cache only.

Current working-tree note:

- There may be a temporary `ImageSimilarityFilter` wired into `Stage4Load`. This plan supersedes that shape. The final implementation should remove model/vector filtering from `Stage4Load` and move it into the new image validation stage.

Target flow:

```text
CrawlService
 -> ProcessService
    -> Stage2CandidateParsing
    -> Stage3ValidationNormalization
 -> ImageValidationService
    -> StageImageValidation
 -> RecipeService
 -> SaveService
    -> Stage4Load
```

The save project must consume `image_validation_*.jsonl`, not `validation_normalization_*.jsonl`, once this stage is enabled.

---

## File Structure

Create:

- `etl/meal/src/projects/image_validation/__init__.py`: package marker.
- `etl/meal/src/projects/image_validation/image_validation_service.py`: locate normalized input files, group by batch, run the validation stage, write success/fail JSONL.
- `etl/meal/src/projects/image_validation/stage_image_validation.py`: per-record image validation stage.
- `etl/meal/src/services/image_validation/__init__.py`: package marker.
- `etl/meal/src/services/image_validation/models.py`: explicit validation result contracts.
- `etl/meal/src/services/image_validation/vectorizer.py`: vectorizer interfaces and CLIP adapter.
- `etl/meal/src/services/image_validation/cache.py`: run-scoped URL-to-vector cache.
- `etl/meal/src/services/image_validation/grouping.py`: per-restaurant similarity grouping.
- `etl/meal/src/services/image_validation/menu_alt.py`: exact review-image URL to ordered-menu alt text enrichment.
- `etl/meal/scripts/render_image_validation_report.py`: local visual report for KEEP/DROP review.
- `etl/meal/tests/test_image_validation_models.py`
- `etl/meal/tests/test_image_vector_cache.py`
- `etl/meal/tests/test_image_vectorizer_contract.py`
- `etl/meal/tests/test_image_similarity_grouping.py`
- `etl/meal/tests/test_stage_image_validation.py`
- `etl/meal/tests/test_image_validation_service.py`
- `etl/meal/tests/test_save_service_image_validation_input.py`
- `etl/meal/tests/test_stage4_image_alt_contract.py`
- `etl/meal/tests/test_local_runner_image_validation_order.py`
- `etl/meal/tests/test_image_validation_report.py`

Modify:

- `etl/meal/src/core/registry.py`: register `StageImageValidation`.
- `etl/meal/src/core/storage/path_builder.py`: map `image_validation` process alias to `cleaning`.
- `etl/meal/src/projects/save/save_service.py`: read `image_validation_*.jsonl` as save input.
- `etl/meal/src/projects/save/stage4_load.py`: remove image vector filtering; use validated image metadata for `alt`.
- `etl/meal/local_pipeline_runner.py`: run image validation before save and include output in snapshots.
- `etl/meal/requirements.txt`: add `sentence-transformers`; keep `numpy` and `Pillow`.

Do not modify:

- DB schema.
- `images` table columns.
- Existing crawler selector behavior, except separate future work for photo pagination.
- Existing raw/candidate/normalized source artifacts.
- Existing hard-delete behavior; this plan still performs no DB deletion.

---

### Task 1: Validation Models

**Files:**
- Create: `etl/meal/src/services/image_validation/__init__.py`
- Create: `etl/meal/src/services/image_validation/models.py`
- Test: `etl/meal/tests/test_image_validation_models.py`

- [ ] **Step 1: Write failing model tests**

Create tests covering kept image metadata, dropped image metadata, stable alt text, and JSON-serializable model dumps.

```python
from src.services.image_validation.models import (
    DroppedImage,
    ImageValidationDecision,
    ValidatedImage,
)


def test_validated_image_adds_group_metadata_and_alt_text():
    source = {"url": "https://cdn.example.com/food.webp", "category": "food"}

    image = ValidatedImage.from_source(
        source,
        group_id="imggrp-001",
        group_order=2,
        nearest_similarity=0.734,
        model_version="clip-ViT-B-32",
    )

    assert image.data["url"] == source["url"]
    assert image.data["validation"]["status"] == "keep"
    assert image.data["validation"]["group_id"] == "imggrp-001"
    assert image.data["validation"]["group_order"] == 2
    assert image.data["validation"]["nearest_similarity"] == 0.734
    assert image.data["validation"]["model_version"] == "clip-ViT-B-32"
    assert image.data["validation"]["alt_text"] == "식당 유사 이미지 그룹 imggrp-001 2번"


def test_dropped_image_records_reason_without_mutating_source():
    source = {"url": "https://cdn.example.com/noise.webp", "category": "food"}

    dropped = DroppedImage.from_source(
        source,
        reason="NO_SIMILAR_IMAGE_IN_STORE",
        nearest_similarity=0.41,
        model_version="clip-ViT-B-32",
    )

    assert "validation" not in source
    assert dropped.data["url"] == source["url"]
    assert dropped.data["validation"]["status"] == "drop"
    assert dropped.data["validation"]["reason"] == "NO_SIMILAR_IMAGE_IN_STORE"


def test_image_validation_decision_is_json_serializable():
    decision = ImageValidationDecision(
        kept_images=[{"url": "https://cdn.example.com/a.webp"}],
        dropped_images=[{"url": "https://cdn.example.com/b.webp"}],
        total_count=2,
        kept_count=1,
        dropped_count=1,
        model_version="clip-ViT-B-32",
    )

    assert decision.to_record()["kept_count"] == 1
```

- [ ] **Step 2: Run model tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_validation_models.py -v
```

Expected: fail because `src.services.image_validation.models` does not exist.

- [ ] **Step 3: Implement model contracts**

Implement:

```python
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
```

- [ ] **Step 4: Run model tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 2: Run-Scoped Vector Cache

**Files:**
- Create: `etl/meal/src/services/image_validation/cache.py`
- Test: `etl/meal/tests/test_image_vector_cache.py`

- [ ] **Step 1: Write failing cache tests**

Cover cache hit/miss, exception not cached, and no cross-run global state.

```python
import pytest

from src.services.image_validation.cache import ImageVectorCache


def test_image_vector_cache_reuses_vector_by_url():
    calls = []

    def provider(url):
        calls.append(url)
        return [1.0, 0.0]

    cache = ImageVectorCache(provider)

    assert cache.get("https://cdn.example.com/a.webp") == [1.0, 0.0]
    assert cache.get("https://cdn.example.com/a.webp") == [1.0, 0.0]
    assert calls == ["https://cdn.example.com/a.webp"]
    assert cache.hit_count == 1
    assert cache.miss_count == 1


def test_image_vector_cache_does_not_cache_failures():
    calls = []

    def provider(url):
        calls.append(url)
        raise OSError("download failed")

    cache = ImageVectorCache(provider)

    with pytest.raises(OSError):
        cache.get("https://cdn.example.com/broken.webp")
    with pytest.raises(OSError):
        cache.get("https://cdn.example.com/broken.webp")
    assert calls == [
        "https://cdn.example.com/broken.webp",
        "https://cdn.example.com/broken.webp",
    ]
```

- [ ] **Step 2: Run cache tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_vector_cache.py -v
```

Expected: fail because `cache.py` does not exist.

- [ ] **Step 3: Implement run-scoped cache**

Implement:

```python
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
```

- [ ] **Step 4: Run cache tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 3: Vectorizer Interface And CLIP Adapter

**Files:**
- Create: `etl/meal/src/services/image_validation/vectorizer.py`
- Modify: `etl/meal/requirements.txt`
- Test: `etl/meal/tests/test_image_vectorizer_contract.py`

- [ ] **Step 1: Write failing vectorizer contract tests**

Tests must not download a model. They verify interface behavior with a fake provider and import-safe CLIP adapter construction.

```python
import pytest

from src.services.image_validation.vectorizer import (
    ImageVectorizer,
    MissingImageVectorizerDependency,
    normalize_vector,
)


def test_normalize_vector_returns_unit_vector():
    vector = normalize_vector([3.0, 4.0])

    assert vector.tolist() == [0.6, 0.8]


def test_image_vectorizer_protocol_with_fake_provider():
    class FakeVectorizer(ImageVectorizer):
        model_version = "fake-image-vectorizer"

        def vectorize(self, url):
            return normalize_vector([1.0, 1.0])

    vectorizer = FakeVectorizer()

    assert vectorizer.model_version == "fake-image-vectorizer"
    assert round(float((vectorizer.vectorize("https://example.com/a.webp") ** 2).sum()), 6) == 1.0


def test_clip_adapter_reports_missing_dependency_cleanly(monkeypatch):
    from src.services.image_validation import vectorizer as module

    monkeypatch.setattr(module, "SentenceTransformer", None)

    with pytest.raises(MissingImageVectorizerDependency):
        module.ClipImageVectorizer(model_name="clip-ViT-B-32")
```

- [ ] **Step 2: Run vectorizer tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_vectorizer_contract.py -v
```

Expected: fail because `vectorizer.py` does not exist.

- [ ] **Step 3: Add dependency contract**

Add to `etl/meal/requirements.txt`:

```text
sentence-transformers
```

Keep:

```text
numpy
Pillow
```

- [ ] **Step 4: Implement vectorizer interface**

Implement:

```python
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
    arr = np.asarray(vector, dtype=np.float32).reshape(-1)
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
```

- [ ] **Step 5: Run vectorizer contract tests**

Run the same test command. Expected: all tests pass without downloading a model.

- [ ] **Step 6: Optional local dependency smoke check**

Run only when dependency install is available:

```powershell
.\.venv\Scripts\python.exe -m pip install -r etl\meal\requirements.txt
.\.venv\Scripts\python.exe -c "from sentence_transformers import SentenceTransformer; print('sentence-transformers ok')"
```

Expected: import succeeds. This command does not instantiate the CLIP model.

---

### Task 4: Per-Restaurant Similarity Grouping

**Files:**
- Create: `etl/meal/src/services/image_validation/grouping.py`
- Test: `etl/meal/tests/test_image_similarity_grouping.py`

- [ ] **Step 1: Write failing grouping tests**

Cover per-record grouping, threshold `0.60`, no cross-store grouping, group ordering, and dropping groups with fewer than 3 images.

```python
from src.services.image_validation.grouping import group_similar_images


def test_group_similar_images_keeps_only_images_in_three_image_groups():
    images = [
        {"url": "a"},
        {"url": "b"},
        {"url": "e"},
        {"url": "c"},
        {"url": "d"},
    ]
    vectors = {
        "a": [1.0, 0.0, 0.0],
        "b": [0.8, 0.2, 0.0],
        "e": [0.7, 0.3, 0.0],
        "c": [0.0, 1.0, 0.0],
        "d": [0.0, 0.0, 1.0],
    }

    decision = group_similar_images(
        images=images,
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )

    assert [image["url"] for image in decision.kept_images] == ["a", "b", "e"]
    assert [image["url"] for image in decision.dropped_images] == ["c", "d"]
    assert decision.kept_images[0]["validation"]["group_id"] == "imggrp-001"
    assert decision.kept_images[2]["validation"]["group_order"] == 3
```

- [ ] **Step 2: Run grouping tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_similarity_grouping.py -v
```

Expected: fail because `grouping.py` does not exist.

- [ ] **Step 3: Implement grouping**

Implementation rules:

- Only compare images passed in one call.
- Normalize all vectors before cosine similarity.
- If vectorization fails for an image, drop it with reason `VECTORIZE_FAILED`.
- If image has no valid URL, drop it with reason `MISSING_IMAGE_URL`.
- Keep images in connected components with size `>= 3`.
- Assign stable group ids in input order: `imggrp-001`, `imggrp-002`.
- Keep input order inside each group.
- Do not compare images from different restaurant records.

- [ ] **Step 4: Run grouping tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 5: StageImageValidation

**Files:**
- Create: `etl/meal/src/projects/image_validation/__init__.py`
- Create: `etl/meal/src/projects/image_validation/stage_image_validation.py`
- Test: `etl/meal/tests/test_stage_image_validation.py`

- [ ] **Step 1: Write failing stage tests**

Cover record-level input/output shape and guarantee that each restaurant record is validated independently.

```python
from src.projects.image_validation.stage_image_validation import StageImageValidation


def test_stage_image_validation_filters_each_record_independently():
    vectors = {
        "store1-a": [1.0, 0.0],
        "store1-b": [0.8, 0.2],
        "store1-c": [0.7, 0.3],
        "store2-a": [0.0, 1.0],
        "store2-b": [0.2, 0.8],
        "store2-c": [0.3, 0.7],
    }
    stage = StageImageValidation(
        vector_provider=lambda url: vectors[url],
        similarity_threshold=0.60,
        model_version="fake",
    )
    records = [
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-1",
            "store": {"name": "Store One"},
            "images": [{"url": "store1-a"}, {"url": "store1-b"}, {"url": "store1-c"}],
        },
        {
            "batch_id": "batch",
            "run_attempt": 1,
            "stage": "validation_normalization",
            "entity_id": "store-2",
            "store": {"name": "Store Two"},
            "images": [{"url": "store2-a"}, {"url": "store2-b"}, {"url": "store2-c"}],
        },
    ]

    validated = stage.execute(records, batch_id="batch", category_cd="SC01", run_attempt=1)

    assert len(validated) == 2
    assert validated[0]["stage"] == "image_validation"
    assert [image["url"] for image in validated[0]["images"]] == ["store1-a", "store1-b", "store1-c"]
    assert [image["url"] for image in validated[1]["images"]] == ["store2-a", "store2-b", "store2-c"]
    assert validated[0]["image_validation"]["kept_count"] == 3
    assert validated[1]["image_validation"]["kept_count"] == 3
```

- [ ] **Step 2: Run stage tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_stage_image_validation.py -v
```

Expected: fail because the image validation project does not exist.

- [ ] **Step 3: Implement stage**

Implementation requirements:

- `NAME = "image_validation"`.
- Input is a list of Stage3 normalized records.
- Output record preserves existing fields.
- Replace `record["images"]` with kept images only.
- Add `record["dropped_images"]`.
- Add `record["image_validation"]` summary.
- Do not mutate input records in place.
- Do not write files in the stage; service writes files.

- [ ] **Step 4: Run stage tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 6: ImageValidationService And Registry

**Files:**
- Create: `etl/meal/src/projects/image_validation/image_validation_service.py`
- Modify: `etl/meal/src/core/registry.py`
- Modify: `etl/meal/src/core/storage/path_builder.py`
- Test: `etl/meal/tests/test_image_validation_service.py`

- [ ] **Step 1: Write failing service tests**

Cover:

- Service reads `validation_normalization_*.jsonl`.
- Service writes `image_validation_*.jsonl`.
- Output path uses `process=cleaning`.
- Batch id is extracted from the normalized filename.
- `run_attempt` is preserved.

```python
from datetime import datetime
from pathlib import Path

from src.core.config import settings
from src.core.storage.jsonl_writer import JsonlWriter
from src.core.storage.path_builder import HivePathBuilder
from src.projects.image_validation.image_validation_service import ImageValidationService


def test_image_validation_service_reads_normalized_and_writes_image_validation(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LAKE_ROOT_PATH", str(tmp_path))
    dt = datetime.now()
    batch_id = "20260527_SC01_001"
    normalized_path = HivePathBuilder.build_path(
        process="normalized",
        service="shop",
        category_cd="SC01",
        stage="validation_normalization",
        batch_id=batch_id,
        status="success",
        dt=dt,
    )
    filename = HivePathBuilder.build_filename(
        "jsonl",
        dt,
        stage="validation_normalization",
        batch_id=batch_id,
        run_attempt=1,
    )
    JsonlWriter.write(normalized_path, filename, [{
        "batch_id": batch_id,
        "run_attempt": 1,
        "store": {"name": "Store"},
        "images": [{"url": "a"}, {"url": "b"}],
    }])

    service = ImageValidationService(
        vector_provider=lambda url: [1.0, 0.0],
        now_provider=lambda: dt,
    )

    result = service.run_image_validation("SC01")

    assert result["processed_batches"] == [batch_id]
    files = list(Path(tmp_path).rglob("image_validation_*.jsonl"))
    assert len(files) == 1
    assert "process=cleaning" in str(files[0])
```

- [ ] **Step 2: Run service tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_validation_service.py -v
```

Expected: fail because service and registry entries do not exist.

- [ ] **Step 3: Register image validation stage**

Modify `registry.py`:

```python
from src.projects.image_validation.stage_image_validation import StageImageValidation

STAGE_IMAGE_VALIDATION = StageImageValidation.NAME

STAGE_MAP = {
    ...
    STAGE_IMAGE_VALIDATION: StageImageValidation,
}
```

- [ ] **Step 4: Add path alias**

Modify `HivePathBuilder.PROCESS_ALIASES`:

```python
"image_validation": "cleaning",
```

- [ ] **Step 5: Implement service**

Service rules:

- Discover today's `validation_normalization_*.jsonl` in `process=cleaning`.
- Group files by batch id.
- Build one `StageImageValidation` per run so cache is handler scoped.
- Write success JSONL with `process="image_validation"` and `stage="image_validation"`.
- Write fail JSONL only for record-level unexpected failures.
- Return `{"processed_batches": [...]}`.

- [ ] **Step 6: Run service tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 7: SaveService Consumes Validated Images

**Files:**
- Modify: `etl/meal/src/projects/save/save_service.py`
- Modify: `etl/meal/src/projects/save/stage4_load.py`
- Test: `etl/meal/tests/test_save_service_image_validation_input.py`
- Test: `etl/meal/tests/test_stage4_image_alt_contract.py`

- [ ] **Step 1: Write failing SaveService input test**

Cover that SaveService reads `image_validation_*.jsonl` and ignores `validation_normalization_*.jsonl` when both exist.

```python
def test_save_service_reads_image_validation_success_files_before_load(monkeypatch, tmp_path):
    # Use HivePathBuilder and JsonlWriter to place both normalized and image_validation files.
    # Monkeypatch Stage4 execute to capture records.
    # Assert captured records contain only validated image list from image_validation file.
```

- [ ] **Step 2: Write failing Stage4 alt test**

Cover that Stage4 uses validation alt text when present and keeps default `"식당 이미지"` when absent.

```python
from src.projects.save.stage4_load import Stage4Load


def test_load_images_uses_validated_alt_text_when_present():
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())
    session = RecordingSession()

    stage._load_images(
        session,
        [{
            "url": "https://cdn.example.com/food.webp",
            "validation": {"alt_text": "식당 유사 이미지 그룹 imggrp-001 1번"},
        }],
        source_table_name="crawling",
        source_id="343",
    )

    assert session.params[0]["image_url"] == (
        '<img src="https://cdn.example.com/food.webp" alt="식당 유사 이미지 그룹 imggrp-001 1번"/>'
    )
```

- [ ] **Step 3: Run SaveService/Stage4 tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_save_service_image_validation_input.py etl\meal\tests\test_stage4_image_alt_contract.py -v
```

Expected: fail because SaveService still reads normalized files and Stage4 ignores validation alt text.

- [ ] **Step 4: Modify SaveService input discovery**

Change SaveService discovery from:

```python
process="normalized"
stage="validation_normalization"
glob("validation_normalization_*.jsonl")
```

to:

```python
process="image_validation"
stage="image_validation"
glob("image_validation_*.jsonl")
```

- [ ] **Step 5: Remove Stage4 direct vector filtering**

If `Stage4Load` currently imports or instantiates `ImageSimilarityFilter`, remove it. Stage4 must trust `record["images"]` from image validation output and perform only DB insert work.

- [ ] **Step 6: Use validated alt text**

Modify `_load_images`:

```python
for img in images:
    if isinstance(img, dict):
        img_url = img.get("url", "")
        alt_text = img.get("validation", {}).get("alt_text", "식당 이미지")
    else:
        img_url = img
        alt_text = "식당 이미지"
    if img_url:
        session.execute(text(QUERY_INSERT_IMAGE), {
            "image_url": self._build_image_tag(img_url, alt_text=alt_text),
            "table_cd": table_cd,
            "table_id": table_id,
        })
```

- [ ] **Step 7: Run tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 8: Local Runner Integration

**Files:**
- Modify: `etl/meal/local_pipeline_runner.py`
- Test: `etl/meal/tests/test_local_runner_image_validation_order.py`

- [ ] **Step 1: Write failing local runner order test**

Patch services and assert order:

```text
CrawlService.run_crawl
ProcessService.run_process
ImageValidationService.run_image_validation
RecipeService.run_recipe
SaveService.run_save
```

- [ ] **Step 2: Run local runner test and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_local_runner_image_validation_order.py -v
```

Expected: fail because `ImageValidationService` is not called.

- [ ] **Step 3: Modify runner imports and orchestration**

Add:

```python
from src.projects.image_validation.image_validation_service import ImageValidationService
```

Add after `ProcessService.run_process(platform, category_cd)`:

```python
ImageValidationService().run_image_validation(category_cd)
```

Keep `RecipeService` and `SaveService` order after image validation.

- [ ] **Step 4: Include image validation artifacts in snapshot**

Add to `stages`:

```python
("image_validation", "image_validation")
```

The snapshot glob must use `HivePathBuilder._normalize_process("image_validation")`, which resolves to `cleaning`.

- [ ] **Step 5: Run local runner test and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 9: Visual Validation Report

**Files:**
- Create: `etl/meal/scripts/render_image_validation_report.py`
- Test: `etl/meal/tests/test_image_validation_report.py`

- [ ] **Step 1: Write failing report tests**

Use a tiny image validation JSONL fixture and assert generated HTML contains store name, KEEP, DROP, group id, and original URL.

- [ ] **Step 2: Run report tests and verify RED**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests\test_image_validation_report.py -v
```

Expected: fail because report script does not exist.

- [ ] **Step 3: Implement report script**

Script behavior:

```powershell
.\.venv\Scripts\python.exe etl\meal\scripts\render_image_validation_report.py `
  --input C:\tmp\sk-connect-image-e2e\run_snapshot\20260527_SC01_001\image_validation_image_validation_success.jsonl `
  --output C:\tmp\sk-connect-image-e2e\image-validation-report.html
```

Output:

- One section per restaurant.
- Green bordered cards for `images`.
- Red bordered cards for `dropped_images`.
- Show group id, group order, nearest similarity, reason, and original URL.
- Use image URL directly in `<img src="...">`; do not download assets in this script.

- [ ] **Step 4: Run report tests and verify GREEN**

Run the same command. Expected: all tests pass.

---

### Task 10: Final Verification

- [ ] **Step 1: Install dependencies**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -r etl\meal\requirements.txt
```

Expected: `numpy`, `Pillow`, and `sentence-transformers` are installed or already satisfied.

- [ ] **Step 2: Run focused image validation suite**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest `
  etl\meal\tests\test_image_validation_models.py `
  etl\meal\tests\test_image_vector_cache.py `
  etl\meal\tests\test_image_vectorizer_contract.py `
  etl\meal\tests\test_image_similarity_grouping.py `
  etl\meal\tests\test_stage_image_validation.py `
  etl\meal\tests\test_image_validation_service.py `
  etl\meal\tests\test_save_service_image_validation_input.py `
  etl\meal\tests\test_stage4_image_alt_contract.py `
  etl\meal\tests\test_local_runner_image_validation_order.py `
  etl\meal\tests\test_image_validation_report.py `
  -v
```

Expected: all focused tests pass.

- [ ] **Step 3: Run full meal ETL test suite**

Run:

```powershell
$env:PYTHONPATH='C:\dev\Project\SK-Connect\etl\meal'
.\.venv\Scripts\python.exe -m pytest etl\meal\tests -v
```

Expected: all tests pass. Pytest cache warnings do not fail the task.

- [ ] **Step 4: Run local one-category pipeline smoke test**

Use the existing one-line `target.csv` test folder:

```powershell
$runDir = "C:\tmp\sk-connect-image-e2e"
Set-Location $runDir
$env:PYTHONPATH = "C:\dev\Project\SK-Connect\etl\meal"
$env:DB_HOST = "localhost"
$env:DB_PORT = "5432"
$env:DB_NAME = "service"
$env:DB_USER = "user"
$env:DB_PASS = "password"
$env:LAKE_ROOT_PATH = "$runDir\_temp_lake"
$env:HEAD_MODE = "False"

C:\dev\Project\SK-Connect\.venv\Scripts\python.exe C:\dev\Project\SK-Connect\etl\meal\local_pipeline_runner.py --platform DiningCode --seed target.csv
```

Expected:

- `run_snapshot/{batch_id}` contains `image_validation_*_success.jsonl`.
- `load_*_success.jsonl` exists.
- DB `images` rows contain only validated images from image validation output.

- [ ] **Step 5: Render visual report**

Run:

```powershell
.\.venv\Scripts\python.exe C:\dev\Project\SK-Connect\etl\meal\scripts\render_image_validation_report.py `
  --input C:\tmp\sk-connect-image-e2e\run_snapshot\<batch_id>\image_validation_image_validation_success.jsonl `
  --output C:\tmp\sk-connect-image-e2e\image-validation-report.html
```

Expected: HTML report opens and shows KEEP/DROP per restaurant.

- [ ] **Step 6: Inspect diff**

Run:

```powershell
git status --short
git diff --stat
```

Expected: only files listed in this plan changed, plus tests.
