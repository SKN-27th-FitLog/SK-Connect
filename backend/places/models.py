# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Maps(models.Model):
    map_id = models.BigAutoField(primary_key=True)
    name = models.TextField(blank=True, null=True)
    category_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='category_cd')
    address_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='address_cd', related_name='maps_address_cd_set')
    address_detail = models.TextField(null=False)
    latitude = models.FloatField(null=False)
    longitude = models.FloatField(null=False)

    class Meta:
        managed = False
        db_table = 'maps'


class Shop(models.Model):
    shop_id = models.BigAutoField(primary_key=True)
    map = models.ForeignKey('places.Maps', null=False, on_delete=models.CASCADE, db_column='map_id')
    category_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='category_cd')
    rating = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'shop'


class Menu(models.Model):
    menu_id = models.BigAutoField(primary_key=True)
    shop = models.ForeignKey('places.Shop', null=False, on_delete=models.DO_NOTHING, db_column='shop_id')
    name = models.CharField(max_length=100, null=False)
    price = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'menu'
