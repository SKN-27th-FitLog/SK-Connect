from rest_framework import serializers
from .models import Posts, PostImage
from users.models import User
from common.models import CodeT
from maps.models import Maps

class CodeTSerializer(serializers.ModelSerializer):
    code = serializers.CharField(source = 'code_info', read_only = True)
    name = serializers.CharField(source = 'cd_name', read_only = True)
    class Meta:
        model = CodeT
        fields = ['code', 'name']

class UserSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source = 'id', read_only = True)
    class Meta:
        model = User
        fields = ['user_id']

class MapsSerializer(serializers.ModelSerializer):
    map_id = serializers.CharField(source = 'id', read_only = True)
    addres_cd = serializers.CharField(source = 'address', read_only = True)
    class Meta:
        model = Maps
        fields = ['map_id', 'address_cd', 'latitude', 'longitude']

class PostImageSerializer(serializers.ModelSerializer):
    image_id = serializers.IntegerField(source = 'id', many = True, read_only = True)
    class Meta:
        model = PostImage
        fields = ['image_id', 'image_url']

class PostSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source = 'Feed_title')
    content = serializers.CharField(source = 'Feed_content')
    post_cd = CodeTSerializer(source = 'post_category_cd', read_only = True)

    class Meta:
        fields= [
            'Feed_id',
            'title',
            'content',
            'created_at',
            'post_cd'
        ]

