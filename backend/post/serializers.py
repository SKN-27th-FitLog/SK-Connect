from rest_framework import serializers
from .models import Posts, ImageURL
from common.models import CodeT
from maps.models import Maps
from foodm.models import FoodMap


class CodeTBaseSerializer(serializers.ModelSerializer): #공통 코드 테이블 기본 정보
    class Meta:
        model = CodeT
        fields = ['cd', 'name'] #코드값과 이름만 노출

class MapBaseSerializer(serializers.ModelSerializer): #공통 위치정보 참조용
    class Meta:
        model = Maps
        fields = ['map_id', 'address_cd', 'address_detail', 'latitude', 'longitude']

'''============================================================='''
class imageSerializer(serializers.ModelSerializer): #이미지 정보
    class Meta:
        model = ImageURL
        fields = ['image_id', 'image_url']

class FoodMapSerializer(serializers.ModelSerializer): #맛집 주소
    class Meta:
        model = FoodMap
        fields = ['map', 'signature_menu']

'''==============================================================='''

class PostBaseSerializer(serializers.ModelSerializer): #post관련 공통으로 사용
    cd_table = CodeTBaseSerializer(source = 'status_cd') #공통 코드 시리얼라이저 사용
    map = MapBaseSerializer(source='map_id') #공통 맵 시리얼라이저 사용
    image = imageSerializer(source='post_image_set') #역참조이므로 _set
    class Meta:
        model = Posts
        fields = [ 'title', 'content']
        read_only_fields = ['post_id','created_at', 'modify_at', 'cd_table', 'map', 'image']

class PostListSerializer(PostBaseSerializer): # 게시글 목록 조회
    status_cd = CodeTBaseSerializer(source='status_cd')
    class Meta(PostBaseSerializer):
        fields = PostBaseSerializer.Meta.fields + []
        
        read_only_fields = fields


class PostDetailSerializer(PostBaseSerializer): # 게시글 상세 조회
    category = serializers.CharField()
    class Meta(PostBaseSerializer):
        fields = PostBaseSerializer.Meta.fields + ['category_cd', 'latitude', 'longitude', 'status_cd']

        read_only_fields = fields


class PostCreateSerializer(PostBaseSerializer): #게시글 생성
    class Meta(PostBaseSerializer):
        fields = PostBaseSerializer.Meta.fields +['category_cd', 'latitude', 'longitude', 'address']

