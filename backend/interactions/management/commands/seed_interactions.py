from django.core.management.base import BaseCommand
from faker import Faker
import random

from posts.models import Post
from interactions.models import Comment, Like


class Command(BaseCommand):
    help = "Seed comments and likes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--comments",
            type=int,
            default=3,
            help="max comments per post"
        )
        parser.add_argument(
            "--likes",
            type=int,
            default=5,
            help="max likes per post"
        )

    def handle(self, *args, **kwargs):
        fake = Faker("ko_KR")

        posts = list(Post.objects.all())

        if not posts:
            self.stdout.write(
                self.style.WARNING("No posts found.")
            )
            return

        comments_to_create = []
        likes_to_create = []

        for post in posts:
            # 댓글 생성
            for _ in range(random.randint(1, kwargs["comments"])):
                comments_to_create.append(
                    Comment(
                        post=post,
                        content=fake.sentence(),
                    )
                )

            # 좋아요 생성
            for _ in range(random.randint(1, kwargs["likes"])):
                likes_to_create.append(
                    Like(
                        post=post
                    )
                )

        Comment.objects.bulk_create(comments_to_create)
        Like.objects.bulk_create(likes_to_create)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {len(comments_to_create)} comments "
                f"and {len(likes_to_create)} likes"
            )
        )