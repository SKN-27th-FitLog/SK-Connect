from django.shortcuts import render
from .models import Maps
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .serializers import PostMarkerSerializer, RestaurantMarkerSerializer

# 지도 마커 전체 목록 조회 View
class MapMarkersView(APIView):

    @extend_schema(
        summary="지도 마커 목록 조회",
        description="게시글 마커와 맛집 마커를 모두 반환합니다.",
        responses={
            200: OpenApiResponse(description="마커 목록 반환 성공")
        }
    )
    def get(self, request):
        # category, address_cd는 FK라 select_related로 한번에 조회
        maps = Maps.objects.select_related("category", "address_cd").prefetch_related("posts_set")

        markers = []
        for m in maps:
            posts = m.posts_set.all()
            # 해당 장소에 연결된 게시글이 있으면 게시글 마커 추가
            if posts.exists():
                for p in posts:
                    markers.append(PostMarkerSerializer(m, context={'post': p}).data)
            
            # 맛집 마커는 게시글 유무와 관계없이 항상 포함
            markers.append(RestaurantMarkerSerializer(m).data)

        return Response({"markers": markers})

# 지도 마커 단건 조회 View
class MapMarkerDetailView(APIView):

    @extend_schema(
        summary="지도 마커 단건 조회",
        description="map_id로 특정 마커 정보를 반환합니다.",
        responses={
            200: OpenApiResponse(description="마커 반환 성공")
        }
    )
    def get(self, request, map_id):
        try:
            m = Maps.objects.select_related("category", "address_cd").prefetch_related("posts_set").get(map_id=map_id)
        except Maps.DoesNotExist:
            return Response({"error": "해당 마커를 찾을 수 없습니다."}, status=404)

        markers = []
        posts = m.posts_set.all()
        # 해당 장소에 연결된 게시글이 있으면 게시글 마커 추가
        if posts.exists():
            for p in posts:
                markers.append(PostMarkerSerializer(m, context={'post': p}).data)
        
        # 맛집 마커도 게시글 유무와 관계없이 항상 포함
        markers.append(RestaurantMarkerSerializer(m).data)

        return Response({"markers": markers})