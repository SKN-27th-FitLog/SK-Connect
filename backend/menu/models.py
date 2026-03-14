from django.db import models
from maps import models as m1

class Menu(models.Model):
    # 메뉴 기본 키
    menu_id = models.BigAutoField(
        primary_key=True
    )

    # 어떤 식당(Maps)에 속한 메뉴인지
    # 한 식당에 여러 메뉴가 있을 수 있음 (1:N 관계)

    # 식당 삭제 시 메뉴도 같이 삭제 

    map = models.ForeignKey(
        m1.Maps,
        on_delete=models.CASCADE,
        db_column='map_id',
        related_name='map_menus'
    )

    # 시그니처 메뉴 이름
    # 식당에 메뉴 정보가 없는 경우도 있으므로 null/blank 사용
    menu_name = models.TextField(
        null=True,
        blank=True,
        verbose_name='시그니처 메뉴'
    )

    class Meta:
        # 실제 DB 테이블 이름
        db_table = 'menu'