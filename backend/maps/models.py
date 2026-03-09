from django.db import models
from common import models as m1
from post import models as m2

# 이름, 업종, 대표메뉴, 주소, 위도, 경도

class Maps(models.Model):
    map_id = models.BigAutoField(primary_key = True)
    name = models.TextField(
        null = True,
        blank = True
    )
    category = models.ForeignKey(
        m1.CodeT, 
        on_delete=models.SET_NULL,
        null = True,
        db_column= "category",
        related_name='category_maps'
    )
    address_cd = models.ForeignKey(
        m1.CodeT,
        on_delete = models.SET_NULL,
        db_column = 'address_cd',
        null = True,
        related_name='address_maps'
    )
    address_detail = models.TextField(
        null = False,
        blank = False
    )
    latitude = models.FloatField(
        null = False,
        blank = False
    )
    longitude = models.FloatField(
        null = False,
        blank = False
    )
    post = models.ForeignKey(
        m2.Posts,
        null = True,
        blank = True,
        on_delete=models.SET_NULL,
        db_column = 'post_id'
    )
    class Meta:
        db_table = 'maps'
