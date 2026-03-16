from rest_framework import serializers
from .models import Maps
from foodm.models import FoodMap


# ==============================
# 게시글 마커 serializer
# ==============================
class PostMarkerSerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField() # "post" 고정값 반환
    post_id = serializers.SerializerMethodField() # 연결된 게시글 id
    title = serializers.SerializerMethodField() # 연결된 게시글 제목
    content = serializers.SerializerMethodField() # 연결된 게시글 내용
    category = serializers.CharField(source='category.name', allow_null=True) # 카테고리 이름
    ad_cd = serializers.CharField(source='address_cd.cd', allow_null=True) # 주소 코드

    class Meta:
        model = Maps
        fields = [
            'type', 'map_id', 'name', 'post_id', 'title', 'content',
            'address_detail', 'ad_cd', 'latitude', 'longitude', 'category'
        ]

    def get_type(self, obj):
        return "post"

    def get_post_id(self, obj):
        post = self.context.get('post') # views에서 넘겨준 게시글 객체
        return post.id if post else None

    def get_title(self, obj):
        post = self.context.get('post')
        return post.title if post else None

    def get_content(self, obj):
        post = self.context.get('post')
        return post.content if post else None


# ==============================
# 맛집 마커 serializer
# ==============================
class RestaurantMarkerSerializer(serializers.ModelSerializer):

    type = serializers.SerializerMethodField() # "restaurant" 고정값 반환
    category = serializers.CharField(source='category.name', allow_null=True) # 카테고리 이름
    ad_cd = serializers.CharField(source='address_cd.cd', allow_null=True) # 주소 코드
    signature_menu = serializers.SerializerMethodField() # 시그니처 메뉴 목록

    class Meta:
        model = Maps
        fields = [
            'type', 'map_id', 'name',
            'address_detail', 'ad_cd', 'latitude', 'longitude',
            'category', 'signature_menu'
        ]

    def get_type(self, obj):
        return "restaurant"

    def get_signature_menu(self, obj):
        # 한 식당에 메뉴가 여러 개일 수 있어서 리스트로 반환
        foodmaps = FoodMap.objects.filter(map=obj)
        return [f.signature_menu for f in foodmaps]