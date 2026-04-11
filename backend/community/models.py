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
    status_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='status_cd')
    post_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='post_cd', related_name='posts_post_cd_set')
    user = models.ForeignKey('users.Users', models.DO_NOTHING, blank=True, null=True, db_column='user_id')
    map = models.ForeignKey('places.Maps', models.SET_NULL, blank=True, null=True, db_column='map_id')
    shop = models.ForeignKey('places.Shop', models.SET_NULL, blank=True, null=True, db_column='shop_id')
    crawling = models.ForeignKey('crawling.Crawling', models.DO_NOTHING, blank=True, null=True, db_column='crawling_id')

    class Meta:
        managed = False
        db_table = 'posts'


class Comments(models.Model):
    comment_id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey('community.Posts', null=False, on_delete=models.CASCADE, db_column='post_id')
    user = models.ForeignKey('users.Users', null=False, on_delete=models.DO_NOTHING, db_column='user_id')
    content = models.TextField(null=False)
    created_at = models.DateTimeField(null=False)
    modify_at = models.DateTimeField(null=False)
    status_cd = models.ForeignKey('common.Codet', null=False, on_delete=models.DO_NOTHING, db_column='status_cd')

    class Meta:
        managed = False
        db_table = 'comments'


class Likes(models.Model):
    like_id = models.BigAutoField(primary_key=True)
    post = models.ForeignKey('community.Posts', null=False, on_delete=models.CASCADE, db_column='post_id')
    user = models.ForeignKey('users.Users', null=False, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        managed = False
        db_table = 'likes'
