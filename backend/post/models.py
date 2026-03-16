from django.db import models
from common import models as m1
from users import models as m2
from post import models as m3

# Create your models here.

class Posts(models.Model):
    id = models.BigAutoField(primary_key = True)
    content = models.TextField(
        null = False,
        blank = False,
        verbose_name = '게시글 본문'
    )
    title = models.CharField(
        max_length = 100,
        null = False,
        verbose_name = '게시글 제목'
    )
    created_at = models.DateTimeField(
    null = False,
    blank = False,
    auto_now_add = True,
    verbose_name = "생성일"
    )
    modify_at = models.DateTimeField(
        null = False,
        blank = False,
        auto_now = True
    )
    status_cd = models.ForeignKey(
    m1.CodeT,
    on_delete=models.SET_NULL,
    null = True,
    related_name = 'posts_status',
    db_column = 'status_cd'
    )
    post_cd = models.ForeignKey(
    m1.CodeT,
    on_delete = models.SET_NULL,
    null = True,
    related_name = 'post_category',
    db_column = 'post_cd'
    )
    user_id = models.ForeignKey(
    m2.User,
    on_delete=models.SET_NULL,
    null = True,
    db_column = 'user_id'
    )
    map = models.ForeignKey(  # 추가
        'maps.Maps',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='map_id'
    )

    class Meta:
        db_table = 'posts'

class ImageURL(models.Model):
    image_id = models.BigAutoField(primary_key = True)
    image_url = models.URLField(
        unique = True,
        null = False,
        blank = False,
        verbose_name = '이미지 링크'
    )
    post = models.ForeignKey(
        m3.Posts,
        on_delete = models.CASCADE,
        db_column = 'post_id'
    )
    class Meta:
        db_table = 'post_image'