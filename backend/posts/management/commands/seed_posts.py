from django.core.management.base import BaseCommand
from faker import Faker
import random

from posts.models import Post, PostImage
from maps.models import Map


class Command(BaseCommand):
    help = "Seed posts with images"

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=10,
            help="number of posts"
        )

    def handle(self, *args, **kwargs):
        total = kwargs["total"]

        fake = Faker("ko_KR")

        maps = list(Map.objects.all())

        if not maps:
            self.stdout.write(
                self.style.WARNING("⚠ Map 데이터 없음 → map=None 생성")
            )

        for _ in range(total):

            post = Post.objects.create(
                title=fake.sentence(nb_words=4),
                content=fake.text(),
                map=random.choice(maps) if maps else None,
            )

            # PostImage 1~3개 생성
            image_count = random.randint(1, 3)

            for _ in range(image_count):
                PostImage.objects.create(
                    post=post,
                    image_url=fake.image_url()
                )

        self.stdout.write(
            self.style.SUCCESS(f" {total} posts seeded!")
        )