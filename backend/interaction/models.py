from django.db import models
from common import models as m1
from post import models as m2

# Create your models here.

class LikeT(models.Model):
    id = models.BigAutoField(primary_key = True)
    post= models.ForeignKey(
        m2.Posts, 
        on_delete=models.CASCADE, 
        verbose_name = 'post_id'
        )
    status= models.ForeignKey(
        m1.CodeT,
        on_delete=models.SET_NULL,
        null = True,
        blank = True,
        verbose_name = 'code_id'
    )
    like_count = models.IntegerField(
        null = False,
        blank = False,
        default = 0,
        verbose_name = '좋아요 수'
    )

class CommentsT(models.Model):
    id = models.BigAutoField(primary_key = True)
    post= models.ForeignKey(
        m2.Posts,
        on_delete=models.CASCADE,
        verbose_name = 'post_id'
    )
    status = models.ForeignKey(
        m1.CodeT,
        on_delete=models.SET_NULL,
        null = True,
        blank = True,
        verbose_name = 'code_id'
    )
    content = models.TextField(
        null = False,
        blank = False,
        verbose_name = '댓글 내용'
    )
    comment_count = models.IntegerField(
        null = False,
        blank = False,
        defalt = 0,
        verbose = '댓글 수'
    )
    created_at = models.DateTimeField(
        null = False,
        blank = False,
        auto_now_add = True,
        verbose_name = "생성일"
    )
