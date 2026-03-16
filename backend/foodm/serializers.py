from rest_framework import serializers
from .models import FoodMap


class FoodMapSerializer(serializers.ModelSerializer):

    map_id = serializers.IntegerField(source='map.map_id')  # 장소 id

    class Meta:
        model = FoodMap
        fields = ['map_id', 'signature_menu']  # 반환할 필드