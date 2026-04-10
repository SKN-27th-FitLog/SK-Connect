# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Users(models.Model):
    user_id = models.BigAutoField(primary_key=True)
    email = models.CharField(unique=True, null=False, max_length=255)
    nickname = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.CharField(max_length=255, blank=True, null=True)
    google_id = models.CharField(unique=True, null=False, max_length=255)
    created_at = models.DateTimeField(null=False)
    status_cd = models.ForeignKey('common.Codet', db_column='status_cd', on_delete=models.DO_NOTHING, null=False)

    class Meta:
        managed = False
        db_table = 'users'
