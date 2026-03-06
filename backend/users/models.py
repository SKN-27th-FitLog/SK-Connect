from django.db import models


class User(models.Model):
    id = models.UUIDField(primary_key = True)
