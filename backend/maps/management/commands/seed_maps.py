from django.core.management.base import BaseCommand
from faker import Faker
import random

from maps.models import Map


class Command(BaseCommand):
    help = "Seed map locations"

    def add_arguments(self, parser):
        parser.add_argument(
            "--total",
            type=int,
            default=10,
            help="number of maps to create"
        )

    def handle(self, *args, **kwargs):
        total = kwargs["total"]

        fake = Faker("ko_KR")

        maps = []

        for _ in range(total):
            # 한국 범위 대충
            latitude = random.uniform(33.0, 38.5)
            longitude = random.uniform(126.0, 129.5)

            maps.append(
                Map(
                    latitude=latitude,
                    longitude=longitude,
                )
            )

        Map.objects.bulk_create(maps)

        self.stdout.write(
            self.style.SUCCESS(f"{total} maps created!")
        )