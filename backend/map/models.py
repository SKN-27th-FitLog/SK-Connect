# map/models.py
from django.db import models

class Map(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()