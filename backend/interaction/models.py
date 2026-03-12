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
    class Meta:
        db_table = 'like'

class CommentsT(models.Model):
    id = models.BigAutoField(primary_key = True)
    post= models.ForeignKey(
        m2.Posts,
        on_delete=models.CASCADE,
        db_column= 'post_id'
    )
    status = models.ForeignKey(
        m1.CodeT,
        on_delete=models.SET_NULL, 
        null = True,
        blank = True,
        db_column = 'status_cd'
    )
    content = models.TextField(
        null = False,
        blank = False
    )
    created_at = models.DateTimeField(
        null = False,
        blank = False,
        auto_now_add = True
    )
    modify_at = models.DateTimeField(
        null = False,
        blank = False,
        auto_now = True
    )
    class Meta:
        db_table = 'comments'