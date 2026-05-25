from src.collectors.platforms.recipe10000_collector import Recipe10000Collector
from src.core.registry import get_collector, get_parser
from src.services.parsers.recipe10000_parser import Recipe10000Parser


def test_recipe10000_collector_builds_search_url_from_keyword():
    collector = Recipe10000Collector()

    url = collector.build_search_url("제육볶음")

    assert url == "https://www.10000recipe.com/recipe/list.html?q=%EC%A0%9C%EC%9C%A1%EB%B3%B6%EC%9D%8C"


def test_recipe10000_collector_and_parser_are_registered():
    assert isinstance(get_collector("Recipe10000"), Recipe10000Collector)
    assert isinstance(get_parser("Recipe10000"), Recipe10000Parser)
