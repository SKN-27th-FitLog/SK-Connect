from src.projects.save.stage4_load import Stage4Load


class FakeScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar(self):
        return self.value


class RecordingSession:
    def __init__(self, scalar_values=None):
        self.params = []
        self.scalar_values = iter(scalar_values or [None, 10, None, 20])

    def execute(self, query, params):
        self.params.append(params)
        return FakeScalarResult(next(self.scalar_values, None))


class FakeCodeRepository:
    def __init__(self):
        self.category_codes = {
            "맛집": "CA77",
            "restaurant": "CA77",
            "CA77": "CA77",
        }
        self.information_codes = {
            "맛집정보": "IC77",
            "meal-information": "IC77",
            "IC77": "IC77",
        }
        self.shop_codes = {
            "SC01": "SC01",
        }
        self.table_codes = {
            "crawling": "TC10",
            "TC10": "TC10",
        }

    def get_category_code(self, key):
        return self.category_codes.get(key)

    def get_information_code(self, key):
        return self.information_codes.get(key)

    def get_shop_code(self, key):
        return self.shop_codes.get(key)

    def get_table_code(self, key):
        return self.table_codes.get(key)


def test_load_map_and_shop_writes_ca_category_to_maps_and_sc_code_to_shop():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "Sample Store",
        "shop_cd": "SC01",
        "address_cd": "LA01",
        "address_detail": "1F",
        "latitude": 37.5,
        "longitude": 127.0,
        "rating": 4.5,
    }

    shop_id, map_id = stage._load_map_and_shop(
        session,
        store,
        {},
        category_cd="CA77",
        shop_cd="SC01",
    )

    assert (shop_id, map_id) == ("20", "10")
    assert session.params[0]["category_cd"] == "CA77"
    assert session.params[2]["shop_cd"] == "SC01"


def test_resolve_code_context_uses_code_table_repository_and_config_keys(monkeypatch):
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())

    context = stage._resolve_code_context("SC01")

    assert context["category_cd"] == "CA77"
    assert context["information_cd"] == "IC77"
    assert context["shop_cd"] == "SC01"


def test_load_crawling_and_reviews_writes_resolved_codes_to_crawling():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "Sample Store",
        "description": "description",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }
    reviews = [{"content": "good", "author": "tester", "keywords": ["kind"], "rating": 5}]

    stage._load_crawling_and_reviews(
        session,
        store,
        reviews,
        map_id="10",
        category_cd="CA77",
        information_cd="IC77",
        shop_cd="SC01",
    )

    store_params = session.params[0]
    review_params = session.params[1]
    assert store_params["category_cd"] == "CA77"
    assert store_params["information_cd"] == "IC77"
    assert store_params["shop_cd"] == "SC01"
    assert review_params["category_cd"] == "CA77"
    assert review_params["information_cd"] == "IC77"
    assert review_params["shop_cd"] == "SC01"


def test_load_crawling_and_reviews_wraps_article_url_before_db_insert():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession()
    store = {
        "name": "Sample Store",
        "description": "description",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }

    stage._load_crawling_and_reviews(
        session,
        store,
        [],
        map_id="10",
        category_cd="CA77",
        information_cd="IC77",
        shop_cd="SC01",
    )

    assert session.params[0]["article_url"] == (
        '<a href="https://example.com/store">Sample Store</a>'
    )


def test_load_images_wraps_image_url_before_db_insert():
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())
    session = RecordingSession()

    stage._load_images(
        session,
        [{"url": "https://cdn.example.com/image.png"}],
        source_table_name="crawling",
        source_id="343",
    )

    assert session.params[0]["image_url"] == (
        '<img src="https://cdn.example.com/image.png" alt="식당 이미지"/>'
    )


def test_load_images_writes_source_table_code_and_source_primary_key():
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())
    session = RecordingSession()

    stage._load_images(
        session,
        [{"url": "https://cdn.example.com/image.png"}],
        source_table_name="crawling",
        source_id="343",
    )

    assert session.params[0]["table_cd"] == "TC10"
    assert session.params[0]["table_id"] == 343
    assert "table_name" not in session.params[0]


def test_load_crawling_and_reviews_returns_store_crawling_id_for_image_source():
    stage = Stage4Load(db=object(), code_repository=object())
    session = RecordingSession(scalar_values=[343])
    store = {
        "name": "Sample Store",
        "description": "description",
        "canonical_url": "https://example.com/store",
        "rating": 4.5,
    }

    crawling_id = stage._load_crawling_and_reviews(
        session,
        store,
        [],
        map_id="10",
        category_cd="CA77",
        information_cd="IC77",
        shop_cd="SC01",
    )

    assert crawling_id == "343"


def test_touch_shop_checked_at_writes_restaurant_codes_to_crawling():
    from src.core.constants import QUERY_TOUCH_SHOP_CHECKED_AT

    assert "information_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert "shop_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert ":information_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
    assert "s.shop_cd" in QUERY_TOUCH_SHOP_CHECKED_AT
