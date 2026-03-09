from django.db import models
from maps.models import Maps
# Create your models here.
class FoodMap(Maps):
    maps_ptr = models.OneToOneField(
        Maps,
        on_delete=models.CASCADE,
        parent_link=True,     
        db_column='map_id'     
    )
    signature_menu = models.TextField(
        null = True,
        blank = True
    )
    class Meta:
        db_table = 'Food_Map'
