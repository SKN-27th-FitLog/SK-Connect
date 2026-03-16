from django.db import models
from maps.models import Maps


class FoodMap(models.Model):

    map = models.ForeignKey(
        Maps,
        on_delete=models.CASCADE,
        db_column='map_id',
        related_name="signature_menus"
    )

    signature_menu = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'Food_Map'