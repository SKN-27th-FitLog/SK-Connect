from rest_framwork import serializers
from .models import Posts, ImageURL
from common.models import CodeT
from maps.models import Maps


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

class FoodMapSerializer()

class PostDetailSerializer(serializers.ModelSerializer): # 게시글 리스트조회, 상세 조회
    cd_table = CodeTBaseSerializer(source = 'status_cd') #공통 코드 시리얼라이저 사용
    map = MapBaseSerializer(source='map_id') #공통 맵 시리얼라이저 사용
    image = imageSerializer(source='post_image_set') #역참조이므로 _set
    category = serializers.
    class Meta:
        model = Posts
        fields = ['']

class PostCreateSerializer(serializers.ModelSerializer): #게시글 생성
    class Meta:
        model = Posts
        fields = ['']