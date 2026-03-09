from rest_framework import serializers
from .models import Posts, ImageURL
from common.models import CodeT
from maps.models import Maps


# -----------------------------
# 코드 / 지도 / 이미지 기본 Serializer
# -----------------------------

class CodeTSerializer(serializers.ModelSerializer):  # 공통 코드 테이블 기본 정보
    class Meta:
        model = CodeT
        fields = ["cd", "name"]


class CodeTCategorySerializer(serializers.ModelSerializer):  # category 응답용 코드 테이블
    code = serializers.CharField(source="cd")  # 모델의 cd 필드를 응답의 code로 노출
    class Meta:
        model = CodeT
        fields = ["code", "name"]


class MapListSerializer(serializers.ModelSerializer):  # 게시글 목록 조회용 지도 정보
    class Meta:
        model = Maps
        fields = ["map_id", "address_cd", "latitude", "longitude"]


class MapDetailSerializer(serializers.ModelSerializer):  # 게시글 상세 조회용 지도 정보
    address = serializers.CharField(source="address_cd")  # address_cd를 address 이름으로 노출

    class Meta:
        model = Maps
        fields = ["map_id", "address", "latitude", "longitude"]


class PostImageSerializer(serializers.ModelSerializer):  # 게시글에 연결된 이미지 정보
    class Meta:
        model = ImageURL
        fields = ["image_id", "image_url"]


# -----------------------------
# Posts ↔ Maps 공통 로직
# -----------------------------

class PostMapMixin:
    # Posts 에 연결된 가장 최신 Maps 레코드를 가져오는 공통 함수
    def _get_latest_map(self, post: Posts):
        return post.maps_set.order_by("-map_id").first()


# -----------------------------
# 게시글 목록 / 상세 조회 Serializer
# -----------------------------

class PostListSerializer(PostMapMixin, serializers.ModelSerializer):
    """게시글 목록 조회 응답 Serializer"""

    post_cd = serializers.SerializerMethodField()   # 게시글 구분 코드 (예: COMMUNITY)
    status_cd = serializers.SerializerMethodField()  # 코드 테이블 정보
    map = serializers.SerializerMethodField()       # 지도 정보
    image = PostImageSerializer(source="imageurl_set", many=True)  # 이미지 리스트

    class Meta:
        model = Posts
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "post_cd",
            "status_cd",
            "map",
            "image",
        ]

    def get_post_cd(self, obj):
        # Posts.post_cd(CodeT)의 cd 값만 꺼내서 문자열로 반환
        return obj.post_cd.cd if obj.post_cd else None

    def get_status_cd(self, obj):
        # 상태 코드(CodeT)의 cd 값만 노출
        return obj.status_cd.cd if obj.status_cd else None

    def get_cd_table(self, obj):
        # Posts.post_cd에 연결된 코드 테이블 전체 정보 반환
        code = obj.post_cd
        if not code:
            return None
        return CodeTSerializer(code).data

    def get_map(self, obj):
        # 가장 최근 Maps 레코드를 가져와 목록용 지도 Serializer로 변환
        map_obj = self._get_latest_map(obj)
        if not map_obj:
            return None
        return MapListSerializer(map_obj).data


class PostDetailSerializer(PostMapMixin, serializers.ModelSerializer):
    """게시글 상세 조회 응답 Serializer"""

    status_cd = serializers.SerializerMethodField()  # 게시글 상태 코드 (예: ACTIVE)
    post_cd = serializers.SerializerMethodField()    # 게시글 구분 코드 (예: COMMUNITY)
    category = serializers.SerializerMethodField()   # 게시글 카테고리 코드/이름
    user = serializers.SerializerMethodField()       # 작성자 id만 노출
    map = serializers.SerializerMethodField()        # 상세용 지도 정보
    images = PostImageSerializer(source="imageurl_set", many=True)  # 이미지 리스트

    class Meta:
        model = Posts
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "status_cd",
            "post_cd",
            "category",
            "user",
            "map",
            "images",
        ]

    def get_status_cd(self, obj):
        # 상태 코드(CodeT)의 cd 값만 노출
        return obj.status_cd.cd if obj.status_cd else None

    def get_post_cd(self, obj):
        # 게시글 구분 코드(CodeT)의 cd 값만 노출
        return obj.post_cd.cd if obj.post_cd else None

    def get_category(self, obj):
        # 지도에 연결된 카테고리(CodeT)를 기준으로 category 구성
        map_obj = self._get_latest_map(obj)
        if not map_obj or not map_obj.category:
            return None
        return CodeTCategorySerializer(map_obj.category).data

    def get_user(self, obj):
        if not obj.user_id:
            return None
        # User 모델 구조에 상관없이 user_id(pk)만 노출
        return {"user_id": obj.user_id.id}

    def get_map(self, obj):
        # 가장 최근 Maps 레코드를 가져와 상세용 지도 Serializer로 변환
        map_obj = self._get_latest_map(obj)
        if not map_obj:
            return None
        return MapDetailSerializer(map_obj).data


class PostCreateSerializer(serializers.Serializer):
    """게시글 생성 요청 Serializer"""

    title = serializers.CharField()
    content = serializers.CharField()

    post_cd = serializers.CharField()
    category_cd = serializers.CharField()

    latitude = serializers.FloatField()
    longitude = serializers.FloatField()
    address = serializers.CharField()

    image_url = serializers.ListField(
        child=serializers.URLField(),
        required=False
    )

    def _get_code_or_error(self, cd_value: str, field_name: str) -> CodeT:
        # CodeT를 조회하다가 없으면 500 대신 400 ValidationError로 변환
        try:
            return CodeT.objects.get(cd=cd_value)
        except CodeT.DoesNotExist:
            raise serializers.ValidationError({
                field_name: [f"유효하지 않은 코드입니다: {cd_value}"]
            })

    def create(self, validated_data):

        image_urls = validated_data.pop("image_url", [])

        post_cd = validated_data.pop("post_cd")
        category= validated_data.pop("category_cd")

        # 상태 코드는 명세에서 별도 입력이 없으므로 기본값 ST01(ACTIVE)로 가정
        status = self._get_code_or_error("ST01", "status_cd")
        post_category = self._get_code_or_error(post_cd, "post_cd")
        map_category = self._get_code_or_error(category, "category_cd")

        # 게시글 생성
        post = Posts.objects.create(
            title=validated_data["title"],
            content=validated_data["content"],
            status_cd=status,
            post_cd=post_category,
        )

        # 지도 생성
        Maps.objects.create(
            post=post,
            category=map_category,
            latitude=validated_data.pop("latitude"),
            longitude=validated_data.pop("longitude"),
            address_cd=validated_data.pop("address"),
        )

        # 이미지 생성
        for url in image_urls:
            ImageURL.objects.create(
                post=post,
                image_url=url,
            )

        return post