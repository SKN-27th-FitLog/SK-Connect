from src.projects.save.stage4_load import Stage4Load


class RecordingSession:
    def __init__(self):
        self.params = []

    def execute(self, query, params):
        self.params.append(params)


class FakeCodeRepository:
    def get_table_code(self, table_name):
        return {"crawling": "TC10"}.get(table_name)


def test_load_images_uses_validated_alt_text_when_present():
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())
    session = RecordingSession()

    stage._load_images(
        session,
        [{
            "url": "https://cdn.example.com/food.webp",
            "validation": {"alt_text": "순대국"},
        }],
        source_table_name="crawling",
        source_id="343",
    )

    assert session.params[0]["image_url"] == (
        '<img src="https://cdn.example.com/food.webp" '
        'alt="순대국"/>'
    )


def test_load_images_keeps_default_alt_text_without_validation_metadata():
    stage = Stage4Load(db=object(), code_repository=FakeCodeRepository())
    session = RecordingSession()

    stage._load_images(
        session,
        [{"url": "https://cdn.example.com/food.webp"}],
        source_table_name="crawling",
        source_id="343",
    )

    assert session.params[0]["image_url"] == (
        '<img src="https://cdn.example.com/food.webp" alt="식당 이미지"/>'
    )
