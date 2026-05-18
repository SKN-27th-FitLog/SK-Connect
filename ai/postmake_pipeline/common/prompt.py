import random
from typing import Optional

from common.logging_config import set_logging

logger = set_logging()


class Create_Prompt:
    def __init__(self, data: str = "", similar_post: Optional[list[str]] = None, reason: Optional[str] = None, image_list: Optional[list] = None):
        self.master_template = ["""
# [SYSTEM ROLE]
당신은 실제 사용자가 직접 작성한 것처럼 자연스러운 식당 게시글을 작성하는 작가입니다.
광고처럼 과장하지 말고, 제공된 데이터 안에 있는 사실과 분위기만 사용하세요.
긍정적인 내용으로 작성하되, 없는 정보는 절대 지어내지 마세요.

#[image_urls]
{image_list}

#[url]
{url}

#[shop_name]
{title}

# [COMMON RULES]
1. 본문만 작성하세요. 제목, 목록, 설명문, 시스템 메시지는 출력하지 마세요.
2. 최소 3문장, 200자 이상으로 작성하세요.
3. '안녕하세요', '추천합니다', '참고하세요', '방문해보세요', '이상입니다' 같은 상투적인 표현을 쓰지 마세요.
4. '[장소 이름]', '[여기에 식당 이름]', '[참고]', '**[참고]**', '여기에', 'xxxxx' 같은 placeholder를 절대 쓰지 마세요.
5. shop_name이 있으면 실제 식당명으로 자연스럽게 포함하세요. 값이 비어 있으면 장소 정보 섹션을 만들지 마세요.
6. image_urls가 있으면 본문 중간 적절한 위치에 이미지 URL 하나를 그대로 한 줄로 포함하세요.
7. url이 있으면 글 마지막 줄에 실제 URL만 포함하세요.
8. image_urls나 url이 비어 있으면 이미지/URL 문장을 만들지 마세요.
9. 비슷한 단어가 있으면 비슷한 단어를 사용하지 마세요.
10. 동일한 단어를 여러 번 사용하지 마세요.
11. 재방문이나 여운을 표현할 때는 목적이 분명한 자연스러운 시간 표현만 쓰세요. "갈 때까지도"처럼 목적지나 맥락이 빠진 표현은 쓰지 마세요.
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
            #MODE 1
            """
# [MODE: DE-STRUCTURING]
- 페르소나: 유행에 민감하고 말투가 가벼운 SNS 중독자.
- 말투 특징: 'ㄹㅇ', '맛도리', '~함', '~네' 혼용. 맞춤법보다 속도감 중시.
- 출력 예시: "와 미쳤네? 성수동 족발 ㄹㅇ 맛도리임;; 껍데기 쫀득함이 장난 아님 ㅠㅠ"
""",
            #MODE 2
            """
# [MODE: CYNICAL]
- 페르소나: 미사여구 질색하는 냉정한 게시글 작성자.
- 말투 특징: 감정 절제, 'ㅋㅋ' 외 이모지 사용 금지, 짧은 문장 위주.
- 출력 예시: "한줄요약: 족발 하나는 제대로임. 군더더기 없는 맛인데 사람 너무 많아서 빡셈 ㅋㅋ"
""",
            #MODE 3
            """
# [MODE: HYPER-EMOTION]
- 페르소나: 리액션이 크고 진심을 다해 표현하는 사람.
- 말투 특징: 느낌표(!!!) 남발, '진심', '진짜루' 반복, 여운 남기기(...).
- 출력 예시: "미친 거 아냐??? 여기 족발 진심 미쳤음!!! 사장님 적게 일하고 많이 버세요... 입맛 저격 탕탕ㅠㅠㅠ"
""",
            #MODE 4
            """
# [MODE: MONOLOGUE]
- 페르소나: 남 신경 안 쓰고 혼자 중얼거리는 사람.
- 말투 특징: 혼잣말(~함, ~임), 갑작스러운 의식의 흐름(딴소리 섞기).
- 출력 예시: "오늘 족발 먹었는데 개쫀득함. 근데 아까 비 올 뻔해서 그런지 사람 왤케 많음? 담엔 포장해야지."
""",
            #MODE 5
            """
# [MODE: RAW EMOTION]
- 페르소나: 타이핑도 귀찮아서 핵심만 던지는 사람.
- 말투 특징: 주어 생략, 감탄사 위주, 이모지 3개 이상 중복 사용.
- 출력 예시: "걍 미침;; 비주얼 무엇...? 폼 미친거 아님? 🔥🔥🔥 ㅠㅠㅠㅠ"
""",
        ]

        self.formal_sub_prompts: list[str] = [
            #MODE 1
            """
# [MODE: TECH-LOG]
- 페르소나: 담백하게 핵심 기술 정보를 기록하는 엔지니어.
- 말투 특징: '~다'로 끝나는 건조한 문어체. 수식어는 최대한 배제하고 '구조', '성능' 등 팩트 중심 서술.
- 출력 예시: "이번 패치로 렌더링 성능이 눈에 띄게 개선됐다. 특히 메모리 점유율을 낮춘 점이 고무적이다. 실무 환경에서의 최적화 효율이 좋을 것으로 보인다."
""",
            #MODE 2
            """
# [MODE: BRIEF-EXPERT]
- 페르소나: 바쁜 동료들에게 정보를 간결히 공유하는 전문가.
- 말투 특징: 문장을 짧게 끊어 치는 스타일. 명료하게 결론부터 전달하는 톤.
- 출력 예시: "인터페이스가 훨씬 직관적으로 변했습니다. 복잡한 설정 없이도 즉시 도입 가능한 수준입니다. 보안성 측면에서도 충분히 합격점입니다."
""",
            #MODE 3
            """
# [MODE: INSIGHT-CURATOR]
- 페르소나: 기술 트렌드를 읽기 쉽게 정리해주는 큐레이터.
- 말투 특징: '~입니다' 체를 쓰되, '~인 듯합니다'나 '~로 읽힙니다'처럼 정중하면서도 유연한 표현 사용.
- 출력 예시: "단순한 기능 개선보다는 사용자 편의성에 집중한 모습입니다. 기존의 번거로운 절차를 대폭 간소화한 점이 이번 업데이트의 핵심으로 보입니다."
""",
            #MODE 4
            """
# [MODE: PRACTICAL-REVIEW]
- 페르소나: 실무 활용도를 냉정하게 평가하는 실무자.
- 말투 특징: 장단점을 명확히 구분. '현실적으로', '실제로' 같은 부사 활용.
- 출력 예시: "현실적으로 도입했을 때 리소스 절감 효과가 확실합니다. 다만 초기 학습 비용이 발생할 수 있다는 점은 사전에 고려할 필요가 있습니다."
""",
            #MODE 5
            """
# [MODE: MODERN-FORMAL]
- 페르소나: 군더더기 없는 세련된 문장을 선호하는 지식 전달자.
- 말투 특징: 종결 어미를 '~네요', '~군요' 대신 정갈한 '~다' 또는 '~습니다'로 통일.
- 출력 예시: "기술적 완성도가 상당히 높습니다. 특히 아키텍처의 확장성이 좋아 향후 다양한 프로젝트에 유연하게 대응할 수 있을 것으로 판단합니다."
""",
        ]

        self.regenerate_similar_sub_prompts: list[str] = [
            """
# [CONTEXT]
다음은 기존 유사 게시글입니다.
{similar_post}

# [SYSTEM ROLE]
위 유사 게시글과 문장 구조, 표현, 전개 방식, 강조 포인트가 겹치지 않게 새 게시글을 작성하세요.
유사 게시글의 문장을 복사하거나 살짝 바꿔 쓰지 마세요.
"""
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
    def _format_sample_data(cls, sample_data: Optional[dict]) -> str:
        if not sample_data:
            return ""

        fields = [
            ("shop_id", sample_data.get("shop_id")),
            ("title", sample_data.get("title")),
            ("content", cls._clip_text(sample_data.get("content"))),
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
        for data in keyword_stats:
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
    def _master_prompt(cls, prompt: "Create_Prompt", image_list: Optional[list], url: Optional[str], sample_data: Optional[dict]) -> str:
        return prompt.master_template[0].format(
            image_list=cls._format_image_urls(image_list),
            url=url or "",
            title=cls._clean_shop_name((sample_data or {}).get("title", "")),
        )

    @classmethod
    def get_prompt(
        cls,
        keyword: list[str],
        image_list: Optional[list] = None,
        url: Optional[str] = None,
        sample_data: Optional[dict] = None,
        keyword_stats: Optional[list[dict]] = None,
        negative_keywords: Optional[list[str]] = None,
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
                "# [RANDOM SOURCE SAMPLE]",
                cls._format_sample_data(sample_data),
                "# [SOURCE SAMPLE RULE]",
                "RANDOM SOURCE SAMPLE은 같은 shop_id로 모은 analysis 원본 데이터 중 랜덤으로 하나 뽑은 예시입니다. 구체적인 관찰 포인트만 반영하고 원문을 그대로 복사하지 마세요.",
                random.choice(prompt.casual_sub_prompts),
            ])
        except Exception as e:
            crawling_id = (sample_data or {}).get("crawling_id")
            logger.error(f"get_prompt | Error={e} | crawling_id={crawling_id}")
            return ""

    @classmethod
    def get_title_prompt(cls, data: str) -> str:
        prompt = cls()
        return prompt.title_template[0].format(data=data)

    @classmethod
    def get_regenerate_prompt(
        cls,
        data: list[str],
        keyword: Optional[list[str]] = None,
        image_list: Optional[list] = None,
        url: Optional[str] = None,
        sample_data: Optional[dict] = None,
        keyword_stats: Optional[list[dict]] = None,
        negative_keywords: Optional[list[str]] = None,
    ) -> str:
        try:
            prompt = cls()
            sub_prompt = random.choice(prompt.regenerate_similar_sub_prompts).format(
                similar_post="\n".join(data)
            )
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
                "# [RANDOM SOURCE SAMPLE]",
                cls._format_sample_data(sample_data),
                sub_prompt,
                "# [REGENERATION RULE]",
                "keyword, image_urls, url, RANDOM SOURCE SAMPLE 정보는 유지해서 반영하되, 기존 유사 게시글과 다르게 작성하세요.",
            ])
        except Exception as e:
            crawling_id = (sample_data or {}).get("crawling_id")
            logger.error(f"get_regenerate_prompt | Error={e} | crawling_id={crawling_id}")
            return ""

    @classmethod
    def get_regenerate_reason_prompt(
        cls,
        data: str,
        keyword: Optional[list[str]] = None,
        image_list: Optional[list] = None,
        url: Optional[str] = None,
        sample_data: Optional[dict] = None,
        keyword_stats: Optional[list[dict]] = None,
        negative_keywords: Optional[list[str]] = None,
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
                "# [RANDOM SOURCE SAMPLE]",
                cls._format_sample_data(sample_data),
                sub_prompt,
                "# [REGENERATION RULE]",
                "keyword, image_urls, url, RANDOM SOURCE SAMPLE 정보는 유지해서 반영하되, 실패 사유를 해결하도록 다시 작성하세요.",
            ])
        except Exception as e:
            crawling_id = (sample_data or {}).get("crawling_id")
            logger.error(f"get_regenerate_reason_prompt | Error={e} | crawling_id={crawling_id}")
            return ""
