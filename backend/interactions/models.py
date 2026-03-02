from django.db import models
from posts.models import Post


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField()


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)