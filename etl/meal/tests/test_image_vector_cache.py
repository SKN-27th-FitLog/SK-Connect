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
    assert cache.hit_count == 0
    assert cache.miss_count == 2


def test_image_vector_cache_is_scoped_to_instance_not_global():
    calls = []

    def provider(url):
        calls.append(url)
        return [len(calls)]

    first_run_cache = ImageVectorCache(provider)
    second_run_cache = ImageVectorCache(provider)

    assert first_run_cache.get("https://cdn.example.com/a.webp") == [1]
    assert second_run_cache.get("https://cdn.example.com/a.webp") == [2]
    assert calls == [
        "https://cdn.example.com/a.webp",
        "https://cdn.example.com/a.webp",
    ]
