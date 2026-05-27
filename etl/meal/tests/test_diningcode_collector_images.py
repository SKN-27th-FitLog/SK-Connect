import pytest

from src.collectors.platforms.diningcode_collector import DiningCodeCollector


class FakePhotoTabLocator:
    def __init__(self, page, tab_type):
        self.page = page
        self.tab_type = tab_type

    @property
    def first(self):
        return self

    async def count(self):
        return 1

    async def is_visible(self):
        return True

    async def click(self):
        self.page.clicked_tabs.append(self.tab_type)
        self.page.active_tab = self.tab_type


class FakeDiningCodePhotoPage:
    def __init__(self):
        self.active_tab = None
        self.clicked_tabs = []
        self.photos_by_tab = {
            "food": [
                {
                    "url": "https://cdn.example.com/food.webp",
                    "nickname": "food-user",
                    "date": "2026-05-27",
                }
            ],
            "interior": [
                {
                    "url": "https://cdn.example.com/interior.webp",
                    "nickname": "interior-user",
                    "date": "2026-05-27",
                }
            ],
            "exterior": [
                {
                    "url": "https://cdn.example.com/exterior.webp",
                    "nickname": "exterior-user",
                    "date": "2026-05-27",
                }
            ],
            "menu_info": [
                {
                    "url": "https://cdn.example.com/menu.webp",
                    "nickname": "menu-user",
                    "date": "2026-05-27",
                }
            ],
        }

    def locator(self, selector):
        for tab_type in self.photos_by_tab:
            if f'data-sort-value="{tab_type}"' in selector:
                return FakePhotoTabLocator(self, tab_type)
        raise AssertionError(f"Unexpected selector: {selector}")

    async def eval_on_selector_all(self, selector, script):
        assert selector == "div#photos_container .photo_box[data-origin]"
        return self.photos_by_tab[self.active_tab]


@pytest.mark.asyncio
async def test_collect_photo_tabs_collects_only_food_photo_section_images():
    collector = DiningCodeCollector()
    page = FakeDiningCodePhotoPage()

    photo_data = await collector._collect_photo_tabs(page)

    assert page.clicked_tabs == ["food"]
    assert list(photo_data) == ["food"]
    assert photo_data["food"] == [
        {
            "url": "https://cdn.example.com/food.webp",
            "nickname": "food-user",
            "date": "2026-05-27",
        }
    ]

