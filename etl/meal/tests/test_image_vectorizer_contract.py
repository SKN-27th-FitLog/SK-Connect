import pytest

from src.services.image_validation.vectorizer import (
    ImageVectorizer,
    MissingImageVectorizerDependency,
    normalize_vector,
)


def test_normalize_vector_returns_unit_vector():
    vector = normalize_vector([3.0, 4.0])

    assert vector.tolist() == [0.6, 0.8]


def test_normalize_vector_keeps_zero_vector():
    vector = normalize_vector([0.0, 0.0])

    assert vector.tolist() == [0.0, 0.0]


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
