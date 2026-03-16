from django.db import models
from maps import models as m1
# Create your models here.
class FoodMap(models.Model):
    maps_prt = models.ForeignKey(
        m1.Maps,
        on_delete=models.CASCADE,
        related_name='foodmap_map_id', 
        db_column='map_id'     
    )
    signature_menu = models.TextField(
        null = True,
        blank = True
    )
    class Meta:
        db_table = 'Food_Map'
