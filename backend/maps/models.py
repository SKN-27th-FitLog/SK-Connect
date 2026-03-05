from django.db import models
from common import models as m1
from post import models as m2

# 이름, 업종, 대표메뉴, 주소, 위도, 경도

class Maps(models.Model):
    id = models.BigAutoField(primary_key = True)
    name = models.CharField(
        max_length = 50,
        null = True,
        blank = True
        )
    business_category = models.ForeignKey(
        m1.CodeT, 
        on_delete=models.SET_NULL,
        null = True
        )
    signature_menu = models.CharField(
        max_length = 50,
        null = True,
        blank = True,
    )
    address = models.TextField(
        null = False,
        blank = False,
        unique = True
    )
    latitude = models.FloatField(
        null = False,
        blank = False
        )
    longitutde = models.FloatField(
        null = False,
        blank = False
    )
    post = models.ForeignKey(
        m2.Posts,
        null = True,
        blank = True,
        on_delete=models.SET_NULL
    )
