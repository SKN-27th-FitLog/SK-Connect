from rest_framework import serializers
from .models import Posts, ImageURL
from common.models import CodeT
from maps.models import Maps
from foodm.models import FoodMap
from users.models import User


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

class UserSerializer(serializers.ModelSerializer): #유저 정보
    class Meta:
        model = User
        fields = ['user_id']

'''==============================================================='''

class PostBaseSerializer(serializers.ModelSerializer):
    map = serializers.SerializerMethodField()
    image = imageSerializer(source='image_url_set', read_only=True)

    class Meta:
        model = Posts
        fields = ['id', 'title', 'content', 'created_at', 'map', 'image']
        read_only_fields = ['id', 'created_at', 'modify_at']

    def get_map(self, obj):
        try:
            # map_obj = Maps.objects.get(post=obj) 
            # return MapBaseSerializer(map_obj).data
            return MapBaseSerializer(obj.map).data  # post→map 방향
        except Exception: # Maps.DoesNotExist
            return None

'''==============================================================='''

class PostListSerializer(PostBaseSerializer):
    cd_table = CodeTBaseSerializer(source='post_cd', read_only=True)
    post_cd = serializers.ReadOnlyField(source='post_cd.cd')

    class Meta(PostBaseSerializer.Meta):
        fields = PostBaseSerializer.Meta.fields\
            + ['post_cd', 'cd_table']

class PostDetailSerializer(PostBaseSerializer):
    category = CodeTBaseSerializer(source='post_cd', read_only=True)    
    status_cd = serializers.ReadOnlyField(source='status_cd.cd')
    post_cd = serializers.ReadOnlyField(source='post_cd.cd')
    user = UserSerializer(source='user_id', read_only=True)

    class Meta(PostBaseSerializer.Meta):
        fields = PostBaseSerializer.Meta.fields\
            + ['status_cd', 'post_cd', 'category', 'user']

class PostCreateSerializer(PostBaseSerializer):
    latitude = serializers.FloatField(write_only=True)
    longitude = serializers.FloatField(write_only=True)
    address_cd = serializers.CharField(write_only=True)
    address_detail = serializers.CharField(write_only=True)
    image_url = serializers.URLField(write_only=True)

    class Meta(PostBaseSerializer.Meta):
        fields = PostBaseSerializer.Meta.fields + [
            'post_cd', 'status_cd', 'latitude', 'longitude', 'address_cd', 'address_detail', 'image_url'
        ]

    def create(self, validated_data):

        latitude = validated_data.pop('latitude')
        longitude = validated_data.pop('longitude')
        address_cd = validated_data.pop('address_cd')
        address_detail = validated_data.pop('address_detail')
        image_urls = validated_data.pop('image_url', [])

        address_code_instance = CodeT.objects.get(cd = address_cd)

        new_map = Maps.objects.create(
            latitude=latitude,
            longitude=longitude,
            address_cd=address_code_instance,
            address_detail=address_detail 
        )

        post = Posts.objects.create(
            map=new_map,
            **validated_data
        )

        for url in image_urls:
            ImageURL.objects.create(post=post, image_url=url)

        return post   
  