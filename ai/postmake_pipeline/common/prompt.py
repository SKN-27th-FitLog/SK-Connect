import csv
import random
from functools import lru_cache
from pathlib import Path
from typing import Optional

from common.logging_config import set_logging

logger = set_logging()

REFERENCE_EXAMPLE_CSV_PATH = Path(__file__).resolve().parents[1] / "temp" / "output_file.csv"


class Create_Prompt:
    def __init__(self, data: str = "", reason: Optional[str] = None, image_list: Optional[list] = None):
        self.master_template = ["""
# [SYSTEM ROLE]
당신은 실제 사용자가 직접 작성한 것처럼 자연스러운 식당 게시글을 작성하는 작가입니다.
광고처럼 과장하지 말고, 제공된 데이터 안에 있는 사실과 분위기만 사용하세요.
긍정적인 내용으로 작성하되, 없는 정보는 절대 지어내지 마세요.

#[image_html]
{image_list}

#[link_html]
{url}

#[shop_name]
{title}

# [COMMON RULES]
1. 본문만 작성하세요. 제목, 목록, 설명문, 시스템 메시지는 출력하지 마세요.
2. 이미지/링크를 제외한 본문 텍스트는 최소 4문장, 230자 이상으로 작성하세요.
3. '안녕하세요', '추천합니다', '참고하세요', '방문해보세요', '이상입니다' 같은 상투적인 표현을 쓰지 마세요.
4. '[장소 이름]', '[여기에 식당 이름]', '[참고]', '**[참고]**', '여기에', 'xxxxx' 같은 placeholder를 절대 쓰지 마세요.
5. shop_name이 있으면 실제 식당명으로 자연스럽게 포함하세요. 값이 비어 있으면 장소 정보 섹션을 만들지 마세요.
6. image_html이 있으면 본문 중간 적절한 위치에 이미지 HTML 한 개를 그대로 한 줄로 포함하세요. 태그나 속성을 바꾸지 마세요.
7. link_html이 있으면 글 마지막 줄에 링크 HTML을 그대로 한 줄로 포함하세요. 태그나 속성을 바꾸지 마세요.
8. image_html이나 link_html이 비어 있으면 이미지/링크 문장을 만들지 마세요.
9. 비슷한 단어가 있으면 비슷한 단어를 사용하지 마세요.
10. 동일한 단어를 여러 번 사용하지 마세요.
11. 재방문이나 여운을 표현할 때는 목적이 분명한 자연스러운 시간 표현만 쓰세요. "갈 때까지도"처럼 목적지나 맥락이 빠진 표현은 쓰지 마세요.
12. SOURCE FACTS에 있는 사실만 본문 재료로 사용하세요. 리뷰에 없는 메뉴명, 재료명, 지명, 고유명사는 새로 만들지 마세요.
13. 구체적인 대상+평가를 최소 2개 이상 포함하세요. 예: 메뉴/재료/식감/양/가격/서비스/매장 분위기.
14. "맛있다", "좋았다", "만족스러웠다", "다시 찾고 싶다"처럼 어느 식당에도 붙일 수 있는 문장만으로 채우지 마세요.
15. KEYWORDS는 보조 신호이고, SOURCE FACTS와 충돌하면 SOURCE FACTS를 우선하세요.
16. SOURCE FACTS나 TOP SOURCE REVIEWS 섹션 제목, 번호, bullet은 출력하지 마세요.
17. image_html과 link_html은 SOURCE FACTS 제한과 별개로 반드시 그대로 포함해야 하는 출력 요소입니다.
18. 본문 밖의 안내문, 참고문, 예시 설명, 사용 안내, 수정 안내를 출력하지 마세요. "요청하신 형식", "작성된 예시", "실제 사용하실 때", "톤앤매너", "수정하시면 됩니다"처럼 작성물 자체를 설명하는 문장은 본문에 절대 넣지 마세요.
"""]

        self.title_template = ["""
# [SYSTEM ROLE]
아래 게시글 본문을 바탕으로 제목 한 줄만 작성하세요.

# [TITLE RULES]
1. 제목은 5자 이상 20자 이하로 작성하세요.
2. 전체 길이는 반드시 100자 이내여야 합니다.
3. 본문 내용을 요약한 자연스러운 제목이어야 합니다.
4. 이모지, 번호, 목록, 따옴표, 부연 설명을 쓰지 마세요.
5. 부정적인 표현을 쓰지 마세요.

# [post]
{data}
"""]

        self.casual_sub_prompts: list[str] = [
            """
# [MODE: CASUAL NOTE]
- 페르소나: 친구에게 짧게 후기 남기는 사람.
- 말투 특징: 과한 감탄은 줄이고 '~더라', '~했음', '~괜찮았다'를 자연스럽게 섞으세요.
- 주의: '진짜', '맛있다', '좋다'만 반복하지 말고 구체 메뉴/식감/양을 붙이세요.
""",
            """
# [MODE: QUICK REVIEW]
- 페르소나: 군더더기 없이 핵심만 적는 방문자.
- 말투 특징: 짧은 문장 2개와 조금 긴 문장 1개를 섞고, 결론을 앞쪽에 둡니다.
- 주의: 한줄요약, 총평, 결론 같은 라벨은 쓰지 마세요.
""",
            """
# [MODE: SMALL TALK]
- 페르소나: 먹으면서 느낀 순서를 편하게 적는 사람.
- 말투 특징: '처음엔', '먹다 보니', '마지막엔' 같은 흐름 표현을 1개만 사용하세요.
- 주의: 방문 상황은 SOURCE FACTS에 있을 때만 넣으세요.
""",
            """
# [MODE: REALISTIC]
- 페르소나: 장점은 말하지만 광고처럼 보이는 말을 싫어하는 사람.
- 말투 특징: 담백한 '~했다', '~느낌이었다', '~편이었다'를 섞습니다.
- 주의: 재방문 의사는 근거 없이 쓰지 마세요.
""",
            """
# [MODE: LIGHT REACTION]
- 페르소나: 감탄은 있지만 과하게 들뜨지 않는 사람.
- 말투 특징: 느낌표는 최대 1개만 쓰고, 구체 평가 뒤에 짧은 반응을 붙입니다.
- 주의: 이모지, 초성, 과격한 표현은 쓰지 마세요.
""",
        ]

        self.formal_sub_prompts: list[str] = [
            """
# [MODE: OBSERVATION]
- 페르소나: 방문 기록을 차분하게 남기는 사람.
- 말투 특징: '~습니다'보다 '~다', '~였다' 중심의 담백한 문장으로 씁니다.
- 주의: 평가 포인트는 메뉴명/대상어와 붙여서 씁니다.
""",
            """
# [MODE: BALANCED REVIEW]
- 페르소나: 음식과 매장 경험을 균형 있게 적는 리뷰어.
- 말투 특징: 메뉴 평가 2문장, 보조 경험 1문장, 전체 인상 1문장으로 구성합니다.
- 주의: 숫자, 가격, 메뉴 구성은 SOURCE FACTS에 있을 때만 씁니다.
""",
            """
# [MODE: DETAIL FIRST]
- 페르소나: 맛의 세부를 먼저 짚는 사람.
- 말투 특징: 첫 문장에 구체 대상어를 넣고, 다음 문장에서 식감/양/국물/간 같은 평가를 설명합니다.
- 주의: 추상적인 칭찬보다 확인 가능한 표현을 우선합니다.
""",
            """
# [MODE: PLACE MEMORY]
- 페르소나: 매장의 분위기나 식사 장면을 자연스럽게 기억하는 사람.
- 말투 특징: 공간/응대/구성 중 SOURCE FACTS에 있는 보조 요소를 한 문장만 넣습니다.
- 주의: 없는 웨이팅, 주차, 가격 정보는 쓰지 마세요.
""",
            """
# [MODE: CLEAN BLOG]
- 페르소나: 블로그 본문처럼 읽히되 광고 문구를 피하는 사람.
- 말투 특징: 자연스러운 존댓말을 쓰되 '~습니다'만 반복하지 말고 '~었어요', '~더라고요'를 섞습니다.
- 주의: 추천, 꼭 가보세요, 인생맛집 같은 표현은 쓰지 마세요.
""",
        ]

        self.writing_angle_prompts: list[str] = [
            "메뉴/음식 자체를 중심으로 쓰세요. 메뉴명과 맛/식감/양 같은 평가를 앞쪽에 배치하세요.",
            "가성비나 양, 한 끼 만족감을 중심으로 쓰세요. 가격 숫자를 새로 만들지 말고 리뷰에서 확인되는 느낌만 사용하세요.",
            "방문 상황이나 함께 간 대상을 중심으로 쓰세요. 부모님, 친구, 혼밥 같은 대상은 SOURCE FACTS에 있을 때만 사용하세요.",
            "서비스, 주차, 웨이팅, 매장 분위기 중 SOURCE FACTS에 있는 보조 경험을 중심으로 쓰세요.",
            "주문 흐름과 먹는 순서를 따라가듯 쓰세요. 메뉴에서 시작해 반찬/양념/마무리 인상으로 자연스럽게 이어가세요.",
        ]

        self.sentence_structure_prompts: list[str] = [
            "첫 문장은 구체 메뉴명이나 대상어로 바로 시작하고, 두 번째 문장에서 평가 이유를 붙이세요.",
            "첫 문장은 방문 상황으로 짧게 시작하고, 다음 문장에서 메뉴와 평가를 구체화하세요.",
            "짧은 문장과 긴 문장을 섞어 쓰세요. 같은 종결 표현을 연속으로 반복하지 마세요.",
            "기대나 인상으로 시작하되, 바로 다음 문장에 SOURCE FACTS의 구체 메뉴/대상 평가를 넣으세요.",
            "문단 흐름은 메뉴 평가 -> 보조 경험 -> 전체 인상 순서로 구성하세요.",
            "첫 문장을 음식 평가로 쓰고, 마지막 문장은 매장 인상이나 식사 만족감으로 닫으세요.",
            "문장마다 주어를 반복하지 말고, 메뉴명은 필요한 곳에만 1~2회 사용하세요.",
        ]

        self.regenerate_reason_sub_prompts: list[str] = [
            """
# [REASON]
아래는 평가 단계에서 실패한 이유입니다.
{reason}

# [SYSTEM ROLE]
위 실패 사유를 해결하도록 게시글을 다시 작성하세요.
기존 문제가 된 표현을 반복하지 말고, 다른 문장 구조와 전개 방식으로 작성하세요.
"""
        ]

    @staticmethod
    def _clip_text(value: Optional[str], limit: int = 700) -> str:
        return str(value or "").strip()[:limit]

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_reference_example_pool(csv_path: str = str(REFERENCE_EXAMPLE_CSV_PATH), pool_size: int = 200) -> tuple[tuple[str, str], ...]:
        if not Path(csv_path).exists():
            return ()

        pool: list[tuple[str, str]] = []
        seen_count = 0
        try:
            with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as file:
                reader = csv.DictReader(file)
                for row in reader:
                    review = str(row.get("Review") or row.get("review") or "").strip()
                    if not review:
                        continue
                    rating = str(row.get("Rating") or row.get("rating") or "").strip()
                    seen_count += 1
                    item = (rating, review)
                    if len(pool) < pool_size:
                        pool.append(item)
                        continue
                    replace_index = random.randint(0, seen_count - 1)
                    if replace_index < pool_size:
                        pool[replace_index] = item
        except Exception as e:
            logger.error(f"load_reference_example_pool | Error={e} | csv_path={csv_path}")
            return ()
        return tuple(pool)

    @classmethod
    def _format_reference_examples(cls, row_count: int = 3) -> str:
        pool = list(cls._load_reference_example_pool())
        if not pool:
            return ""

        examples = random.sample(pool, k=min(row_count, len(pool)))
        lines = []
        for idx, (rating, review) in enumerate(examples, start=1):
            rating_line = f"  - rating: {rating}" if rating else ""
            review_line = f"  - review: {cls._clip_text(review, 180)}"
            body = "\n".join(line for line in (rating_line, review_line) if line)
            lines.append(f"[{idx}]\n{body}")
        return "\n".join(lines)

    @staticmethod
    def _clean_shop_name(value: Optional[str]) -> str:
        text = str(value or "").strip()
        if text.lower().startswith("review -"):
            return text.split("-", 1)[1].strip()
        return text

    @staticmethod
    def _format_image_urls(image_list: Optional[list]) -> str:
        urls = []
        for image in image_list or []:
            url = None
            if isinstance(image, dict):
                url = image.get("image_url") or image.get("url")
            elif image is not None:
                url = str(image)
            if url:
                urls.append(str(url))
        return "\n".join(urls)

    @classmethod
    def _format_sample_data(cls, sample_data: Optional[dict | list[dict]]) -> str:
        if not sample_data:
            return ""

        if isinstance(sample_data, list):
            lines = []
            for idx, review in enumerate(sample_data[:5], start=1):
                if not isinstance(review, dict):
                    continue
                fields = [
                    ("title", review.get("title")),
                    ("content", cls._clip_text(review.get("content"), 280)),
                    ("keywords", review.get("keywords")),
                    ("sentimental", review.get("sentimental")),
                    ("score", review.get("score")),
                ]
                body = "\n".join(
                    f"  - {key}: {value}"
                    for key, value in fields
                    if value not in (None, "")
                )
                if body:
                    lines.append(f"[{idx}]\n{body}")
            return "\n".join(lines)

        fields = [
            ("shop_id", sample_data.get("shop_id")),
            ("title", sample_data.get("title")),
            ("content", cls._clip_text(sample_data.get("content"), 280)),
            ("keywords", sample_data.get("keywords")),
            ("sentimental", sample_data.get("sentimental")),
            ("score", sample_data.get("score")),
        ]
        return "\n".join(f"- {key}: {value}" for key, value in fields if value not in (None, ""))

    @staticmethod
    def _format_keyword_stats(keyword_stats: Optional[list[dict]]) -> str:
        if not keyword_stats:
            return ""
        lines = []
        for data in keyword_stats[:10]:
            lines.append(
                "- {keyword} | batch_count={batch_count} | average_score={average_score} | final_weight={final_weight}".format(
                    keyword=data.get("keyword"),
                    batch_count=data.get("batch_count"),
                    average_score=data.get("average_score"),
                    final_weight=data.get("final_weight"),
                )
            )
        return "\n".join(lines)

    @staticmethod
    def _format_negative_keywords(negative_keywords: Optional[list[str]]) -> str:
        if not negative_keywords:
            return ""
        return ", ".join(negative_keywords[:5])

    @classmethod
    def _master_prompt(cls, prompt: "Create_Prompt", image_list: Optional[list], url: Optional[str], sample_data: Optional[dict | list[dict]]) -> str:
        shop_sample = sample_data
        if isinstance(sample_data, list):
            shop_sample = sample_data[0] if sample_data else {}
        return prompt.master_template[0].format(
            image_list=cls._format_image_urls(image_list),
            url=url or "",
            title=cls._clean_shop_name((shop_sample or {}).get("title", "")),
        )

    @classmethod
    def get_prompt(
        cls,
        keyword: list[str],
        image_list: Optional[list] = None,
        url: Optional[str] = None,
        sample_data: Optional[dict | list[dict]] = None,
        keyword_stats: Optional[list[dict]] = None,
        negative_keywords: Optional[list[str]] = None,
        source_facts: Optional[str] = None,
    ) -> str:
        try:
            prompt = cls()
            return "\n".join([
                cls._master_prompt(prompt, image_list, url, sample_data),
                "# [KEYWORDS]",
                ", ".join(keyword),
                "# [KEYWORD PRIORITY]",
                cls._format_keyword_stats(keyword_stats),
                "# [KEYWORD PRIORITY RULE]",
                "final_weight가 높은 키워드를 우선 반영하되, 숫자나 점수 자체를 본문에 쓰지 마세요.\n"
                "메뉴명이나 대상어가 붙은 키워드는 해당 메뉴/대상에 대한 평가로만 사용하고, 일반 맛 평가처럼 섞어 쓰지 마세요.",
                "# [AVOID KEYWORDS]",
                cls._format_negative_keywords(negative_keywords),
                "# [AVOID KEYWORD RULE]",
                "AVOID KEYWORDS에 있는 요소는 장점처럼 강조하지 말고, 가능한 한 언급하지 마세요.",
                "# [WRITING ANGLE]",
                random.choice(prompt.writing_angle_prompts),
                "# [SENTENCE STRUCTURE]",
                random.choice(prompt.sentence_structure_prompts),
                "# [REFERENCE WRITING EXAMPLES]",
                cls._format_reference_examples(),
                "# [REFERENCE EXAMPLE RULE]",
                "REFERENCE WRITING EXAMPLES는 문장 밀도와 구체성 참고용입니다.\n"
                "예시의 메뉴명, 장소명, 사실관계는 절대 가져오지 말고 SOURCE FACTS와 TOP SOURCE REVIEWS에 있는 사실만 사용하세요.",
                "# [TOP SOURCE REVIEWS]",
                cls._format_sample_data(sample_data),
                "# [SOURCE REVIEW RULE]",
                "TOP SOURCE REVIEWS는 선정 키워드와 많이 겹치고 메뉴명/대상어가 있는 리뷰를 우선 고른 근거입니다.\n"
                "여러 리뷰에서 반복되는 구체적인 관찰 포인트를 반영하되, 원문을 그대로 복사하지 마세요.",
                "# [SOURCE FACTS]",
                str(source_facts or "").strip(),
                "# [SOURCE FACT RULE]",
                "본문은 SOURCE FACTS의 사실만 조합해서 작성하세요.\n"
                "SOURCE FACTS가 부족하면 TOP SOURCE REVIEWS에서 직접 확인되는 표현만 보완하고, 추측으로 메뉴명/재료명/장소명을 만들지 마세요.\n"
                "SOURCE FACTS를 모두 나열하지 말고 메뉴/맛·식감·양/서비스·분위기·가격·상황 중 서로 다른 축 3개 안팎을 골라 조합하세요.",
                "# [PASS CHECK BEFORE OUTPUT]",
                "출력 전 스스로 확인하세요. 본문 텍스트가 이미지/링크를 제외하고 4문장 이상, 230자 이상이어야 합니다.\n"
                "SOURCE FACTS 또는 TOP SOURCE REVIEWS에서 확인되는 구체 대상어+평가를 최소 2개 넣어야 합니다.\n"
                "가격, 메뉴 구성, 무한리필, 주차, 웨이팅 같은 정보는 근거에 정확히 있을 때만 씁니다.",
                random.choice(prompt.casual_sub_prompts + prompt.formal_sub_prompts),
            ])
        except Exception as e:
            sample_for_log = sample_data[0] if isinstance(sample_data, list) and sample_data else sample_data
            crawling_id = (sample_for_log or {}).get("crawling_id")
            logger.error(f"get_prompt | Error={e} | crawling_id={crawling_id}")
            return ""

    @classmethod
    def get_title_prompt(cls, data: str) -> str:
        prompt = cls()
        return prompt.title_template[0].format(data=data)

    @classmethod
    def get_regenerate_reason_prompt(
        cls,
        data: str,
        keyword: Optional[list[str]] = None,
        image_list: Optional[list] = None,
        url: Optional[str] = None,
        sample_data: Optional[dict | list[dict]] = None,
        keyword_stats: Optional[list[dict]] = None,
        negative_keywords: Optional[list[str]] = None,
        source_facts: Optional[str] = None,
        previous_post: Optional[str] = None,
    ) -> str:
        try:
            prompt = cls()
            sub_prompt = random.choice(prompt.regenerate_reason_sub_prompts).format(reason=data)
            return "\n".join([
                cls._master_prompt(prompt, image_list, url, sample_data),
                "# [KEYWORDS]",
                ", ".join(keyword or []),
                "# [KEYWORD PRIORITY]",
                cls._format_keyword_stats(keyword_stats),
                "# [KEYWORD PRIORITY RULE]",
                "final_weight가 높은 키워드를 우선 반영하되, 숫자나 점수 자체를 본문에 쓰지 마세요.\n"
                "메뉴명이나 대상어가 붙은 키워드는 해당 메뉴/대상에 대한 평가로만 사용하고, 일반 맛 평가처럼 섞어 쓰지 마세요.",
                "# [AVOID KEYWORDS]",
                cls._format_negative_keywords(negative_keywords),
                "# [AVOID KEYWORD RULE]",
                "AVOID KEYWORDS에 있는 요소는 장점처럼 강조하지 말고, 가능한 한 언급하지 마세요.",
                "# [WRITING ANGLE]",
                random.choice(prompt.writing_angle_prompts),
                "# [SENTENCE STRUCTURE]",
                random.choice(prompt.sentence_structure_prompts),
                "# [REFERENCE WRITING EXAMPLES]",
                cls._format_reference_examples(),
                "# [REFERENCE EXAMPLE RULE]",
                "REFERENCE WRITING EXAMPLES는 문장 밀도와 구체성 참고용입니다.\n"
                "예시의 메뉴명, 장소명, 사실관계는 절대 가져오지 말고 SOURCE FACTS와 TOP SOURCE REVIEWS에 있는 사실만 사용하세요.",
                "# [TOP SOURCE REVIEWS]",
                cls._format_sample_data(sample_data),
                "# [SOURCE FACTS]",
                str(source_facts or "").strip(),
                "# [PREVIOUS POST]",
                str(previous_post or "").strip(),
                sub_prompt,
                "# [REGENERATION RULE]",
                "PREVIOUS POST를 그대로 고치지 말고, 실패 사유가 된 표현을 제거한 뒤 SOURCE FACTS에 있는 사실만 사용해서 새로 작성하세요.\n"
                "구체적인 대상+평가를 최소 2개 이상 포함하고, 상투적인 칭찬만 반복하지 마세요.\n"
                "PREVIOUS POST와 다른 관점/문장 순서로 쓰고, SOURCE FACTS 중 서로 다른 축의 사실을 골라 조합하세요.",
                "# [PASS CHECK BEFORE OUTPUT]",
                "출력 전 스스로 확인하세요. 본문 텍스트가 이미지/링크를 제외하고 4문장 이상, 230자 이상이어야 합니다.\n"
                "평가 실패 사유에 나온 문제를 반복하지 말고, 근거 없는 가격/메뉴/시설 정보는 모두 빼세요.",
                random.choice(prompt.casual_sub_prompts + prompt.formal_sub_prompts),
            ])
        except Exception as e:
            sample_for_log = sample_data[0] if isinstance(sample_data, list) and sample_data else sample_data
            crawling_id = (sample_for_log or {}).get("crawling_id")
            logger.error(f"get_regenerate_reason_prompt | Error={e} | crawling_id={crawling_id}")
            return ""
