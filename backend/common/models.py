# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Codet(models.Model):
    cd = models.CharField(primary_key=True, max_length=6)
    name = models.CharField(max_length=30, null=False)
    cd_info = models.TextField(null=False)
    cd_upper = models.CharField(max_length=6, blank=True, null=True)

    class Meta:
        db_table = 'codeT'


class Images(models.Model):
    image_id = models.BigAutoField(primary_key=True)
    image_url = models.CharField(max_length=500, null=False)
    table_name =models.ForeignKey(ContentType, null=False, on_delete=models.CASCADE)
    table_id = models.BigIntegerField(null=False)
    content_object = GenericForeignKey('table_name', 'table_id') # 연결된 모델 인스턴스/ ERD상에는 없음

    class Meta:
        db_table = 'images'
