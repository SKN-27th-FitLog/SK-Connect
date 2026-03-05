from tkinter import CASCADE
from django.db import models
from common import models as m1
from users import models as m2
from post import models as m3

# Create your models here.

class Posts(models.Model):
    Feed_content = models.TextField(
        null = False,
        blank = False,
        verbose_name = '게시글 본문'
    )
    Feed_title = models.CharField(
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
    status_id = models.ForeignKey(
    m1.CodeT,
    on_delete=models.CASCADE,
    verbose_name = '상태코드',
    related_name = 'posts_status'
    )
    post_category_cd = models.ForeignKey(
    m1.CodeT,
    on_delete = models.SET_NULL,
    null = True,
    verbose_name = '카테고리 코드',
    related_name = 'post_category'
    )
    user_id = models.ForeignKey(
    m2.User,
    on_delete=models.SET_NULL,
    null = True
    )

class ImageURL(models.Model):
    Image_url = models.TextField(primary_key = True)
    post = models.ForeignKey(
        m3.Posts,
        on_delete = models.CASCADE,
        verbose_name = '게시글 아이디'
    )