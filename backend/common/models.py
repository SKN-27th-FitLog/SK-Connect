from django.db import models


# Create your models here.

class CodeT(models.Model):
    cd = models.CharField(                    # 코드 (문자(=2) + 숫자(=2))
        max_length = 6,
        primary_key = True
    )
    name = models.CharField(                     # 코드명
        null = False,
        blank = False,
        max_length = 30,
        unique = True,
        editable = False
    )
    cd_info = models.TextField(                     # 코드설명
        editable = False,
        null = False,
        blank = False
    )
    cd_upper = models.CharField(                    # 상위코드 => 코드 
        max_length = 6,
        null = True,
        blank = True,
        editable = False
    )
    class Meta:
        db_table = 'codeT'
    