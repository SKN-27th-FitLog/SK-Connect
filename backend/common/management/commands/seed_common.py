from django.core.management.base import BaseCommand
from common.models import Code


class Command(BaseCommand):
    help = "Seed common codes"

    def handle(self, *args, **kwargs):

        codes = [
            # 게시글 카테고리
            {"group": "POST_CATEGORY", "code": "FREE", "name": "자유"},
            {"group": "POST_CATEGORY", "code": "INFO", "name": "정보"},
            {"group": "POST_CATEGORY", "code": "QUESTION", "name": "질문"},

            # 게시글 상태
            {"group": "POST_STATUS", "code": "ACTIVE", "name": "활성"},
            {"group": "POST_STATUS", "code": "DELETED", "name": "삭제"},
            {"group": "POST_STATUS", "code": "HIDDEN", "name": "숨김"},

            # 좋아요 타입 예시
            {"group": "REACTION_TYPE", "code": "LIKE", "name": "좋아요"},
            {"group": "REACTION_TYPE", "code": "LOVE", "name": "좋아요+"},
        ]

        created_count = 0

        for data in codes:
            _, created = Code.objects.get_or_create(
                group=data["group"],
                code=data["code"],
                defaults={"name": data["name"]},
            )

            if created:
                created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{created_count} codes created (duplicates skipped)"
            )
        )