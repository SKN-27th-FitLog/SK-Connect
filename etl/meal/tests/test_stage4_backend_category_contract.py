from src.core.constants import RESTAURANT_CATEGORY_CD
from src.projects.save.stage4_load import Stage4Load


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class RecordingSession:
    def __init__(self):
        self.params = []
        self.scalar_values = iter([None, 10, None, 20])

    def execute(self, query, params):
        self.params.append(params)
        return FakeScalarResult(next(self.scalar_values, None))


def test_load_map_and_shop_writes_ca_category_to_maps_and_sc_code_to_shop():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "테스트 식당",
        "shop_cd": "SC01",
        "address_cd": "LA01",
        "address_detail": "1층",
        "latitude": 37.5,
        "longitude": 127.0,
        "rating": 4.5,
    }

    shop_id, map_id = stage._load_map_and_shop(session, store, {}, "SC01")

    assert (shop_id, map_id) == ("20", "10")
    assert session.params[0]["category_cd"] == RESTAURANT_CATEGORY_CD
    assert session.params[2]["shop_cd"] == "SC01"


def test_load_crawling_and_reviews_writes_ca_category_to_crawling():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "테스트 식당",
        "description": "설명",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }
    reviews = [{"content": "좋아요", "author": "tester", "keywords": ["친절"], "rating": 5}]

    stage._load_crawling_and_reviews(session, store, reviews, map_id="10", category_cd="SC01")

    assert session.params[0]["category_cd"] == RESTAURANT_CATEGORY_CD
    assert session.params[1]["category_cd"] == RESTAURANT_CATEGORY_CD


def test_load_crawling_and_reviews_wraps_article_url_before_db_insert():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "Sample Store",
        "description": "description",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }

    stage._load_crawling_and_reviews(session, store, [], map_id="10", category_cd="SC01")

    assert session.params[0]["article_url"] == (
        '<a href="https://example.com/store">Sample Store</a>'
    )


def test_load_images_wraps_image_url_before_db_insert():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()

    stage._load_images(session, [{"url": "https://cdn.example.com/image.png"}], shop_id="20")

    assert session.params[0]["image_url"] == (
        '<img src="https://cdn.example.com/image.png" alt="식당 이미지"/>'
    )
