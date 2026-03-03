from django.db import models
from maps.models import Map


class Post(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()

    map = models.ForeignKey(
        "maps.Map",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
)


class PostImage(models.Model):
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image_url = models.CharField(max_length=255)