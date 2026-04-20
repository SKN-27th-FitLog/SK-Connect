# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Posts(models.Model):
    post_id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=100, null=False)
    content = models.TextField(null=False)
    created_at = models.DateTimeField(null=False)
    modify_at = models.DateTimeField(null=False)
    status_cd = models.ForeignKey('common.Codet', db_column='status_cd',null=False, on_delete=models.DO_NOTHING, related_name='+')
    post_cd = models.ForeignKey('common.Codet', db_column='post_cd', null=False, on_delete=models.DO_NOTHING, related_name='+')
    user_id = models.ForeignKey('users.Users',  on_delete=models.DO_NOTHING)
    map_id = models.ForeignKey('places.Maps', blank=True, null=True, on_delete=models.DO_NOTHING)
    shop_id = models.ForeignKey('places.Shop', blank=True, null=True, on_delete=models.DO_NOTHING)
    crawling_id = models.ForeignKey('crawling.Crawling', blank=True, null=True, on_delete=models.CASCADE)
    class Meta:
        managed = False
        db_table = 'posts'

class Comments(models.Model):
    comment_id = models.BigAutoField(primary_key=True)
    post_id = models.ForeignKey('community.Posts', db_column ='post_id', on_delete=models.CASCADE, blank=True, null=True)
    crawling = models.ForeignKey('crawling.Crawling', db_column='crawling_id', on_delete=models.CASCADE, blank=True, null=True)
    user = models.ForeignKey('users.Users', db_column='user_id',null=False, on_delete=models.DO_NOTHING)
    content = models.TextField(null=False)
    created_at = models.DateTimeField(null=False)
    modify_at = models.DateTimeField(null=False)
    status_cd = models.ForeignKey('common.Codet', db_column='status_cd', null=False, on_delete=models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'comments'

class Likes(models.Model):
    like_id = models.BigAutoField(primary_key=True)
    post_id = models.ForeignKey('community.Posts', null=False, on_delete=models.CASCADE)
    user_id = models.ForeignKey('users.Users', null=False, on_delete=models.CASCADE)

    class Meta:
        managed = False
        db_table = 'likes'