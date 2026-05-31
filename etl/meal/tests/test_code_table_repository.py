from src.core.repository.code_table_repository import CodeTableRepository


CODE_ROWS = [
    {"cd": "CA00", "name": "category_cd", "cd_info": "category", "cd_upper": None},
    {"cd": "CA01", "name": "맛집", "cd_info": "restaurant", "cd_upper": "CA00"},
    {"cd": "IC00", "name": "information_cd", "cd_info": "information", "cd_upper": None},
    {"cd": "IC01", "name": "맛집정보", "cd_info": "meal information", "cd_upper": "IC00"},
    {"cd": "SC00", "name": "shop_cd", "cd_info": "shop", "cd_upper": None},
    {"cd": "SC01", "name": "한식", "cd_info": "korean food", "cd_upper": "SC00"},
    {"cd": "TC00", "name": "table_cd", "cd_info": "table", "cd_upper": None},
    {"cd": "TC10", "name": "crawling", "cd_info": "crawling table", "cd_upper": "TC00"},
]


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query):
        return FakeResult(self.rows)


class FakeDB:
    def __init__(self, rows):
        self.rows = rows

    def get_session(self):
        return FakeSession(self.rows)


def test_code_table_repository_resolves_category_information_shop_and_table_codes_from_codet():
    repo = CodeTableRepository(db=FakeDB(CODE_ROWS))

    assert repo.get_category_code("맛집") == "CA01"
    assert repo.get_category_code("CA01") == "CA01"
    assert repo.get_information_code("맛집정보") == "IC01"
    assert repo.get_information_code("IC01") == "IC01"
    assert repo.get_shop_code("한식") == "SC01"
    assert repo.get_shop_code("SC01") == "SC01"
    assert repo.get_table_code("crawling") == "TC10"
