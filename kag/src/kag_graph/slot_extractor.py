from kag_graph.models import ExtractedSlot


class SlotExtractor:
    def extract(self, raw_text: str, domain: str, intent: str) -> list[ExtractedSlot]:
        slots: list[ExtractedSlot] = []

        if "중국집" in raw_text or "중국음식" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Menu", "중국집", "중국음식", 0.9, False, True))
        if "카페" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Menu", "카페", "카페", 0.9, False, True))
        if "면" in raw_text and any(token in raw_text for token in ("싫", "말고", "제외", "빼줘")):
            slots.append(ExtractedSlot("negative_condition", "Ingredient", "면", "면", 0.9, True, True))
        if "조용한" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Tag", "조용한", "조용한", 0.9, False, True))
        if "시끄러운" in raw_text and any(token in raw_text for token in ("말고", "싫", "제외", "빼줘")):
            slots.append(ExtractedSlot("negative_condition", "Tag", "시끄러운", "시끄러운", 0.9, True, True))
        if "GPT" in raw_text:
            slots.append(ExtractedSlot("positive_condition", "Technology", "GPT", "gpt", 0.9, False, True))
        if "업데이트" in raw_text:
            slots.append(ExtractedSlot("event", "Event", "업데이트", "업데이트", 0.9, False, True))
        if "판교" in raw_text:
            slots.append(ExtractedSlot("concept", "Concept", "판교", "판교", 0.9, False, True))

        return slots
