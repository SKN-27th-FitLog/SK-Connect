from django.shortcuts import render
from .models import Maps
# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

class MapMarkersView(APIView):

    @extend_schema(
        summary="지도 마커 목록 조회",
        description="게시글 마커와 맛집 마커를 모두 반환합니다.",
        responses={
            200: OpenApiResponse(
                description="마커 목록 반환 성공",
                examples=[
                    OpenApiExample(
                        name="성공 예시",
                        value={
                            "markers": [
                                {
                                    "type": "post",
                                    "post_id": 1,
                                    "title": "강남 한식 맛집 추천",
                                    "content": "강남역 근처 불고기집 정말 맛있습니다.",
                                    "address_cd": "LA163",
                                    "latitude": 37.6409453,
                                    "longitude": 126.9378687,
                                    "category": "한식"
                                },
                                {
                                    "type": "restaurant",
                                    "name": "1인1잔",
                                    "address_cd": "LA163",
                                    "latitude": 37.6409453,
                                    "longitude": 126.9378687,
                                    "category": "카페",
                                    "signature_menu": "아메리카노"
                                }
                            ]
                        }
                    )
                ]
            )
        }
    )
    
    def get(self, request):

        maps = Maps.objects.select_related(
            "post",
            "category"
        )

        markers = []

        for m in maps:

            # 게시글 마커
            if m.post:
                markers.append({
                    "type": "post",
                    "post_id": m.post.id,
                    "title": m.post.title,
                    "content": m.post.content,
                    "address_cd": m.address_cd,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "category": m.category.name if m.category else None
                })

            # 맛집 마커
            else:
                markers.append({
                    "type": "restaurant",
                    "name": m.name,
                    "address_cd": m.address_cd,
                    "latitude": m.latitude,
                    "longitude": m.longitude,
                    "category": m.category.name if m.category else None,
                })

        return Response({"markers": markers})