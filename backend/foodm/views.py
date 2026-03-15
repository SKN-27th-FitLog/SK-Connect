from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import FoodMap

class FoodMapView(APIView):

    @extend_schema(
        summary="맛집 마커 조회",
        description="지도에서 맛집 마커 클릭 시 해당 맛집의 시그니처 메뉴를 반환합니다.",
        responses={
            200: OpenApiResponse(
                description="맛집 마커 정보 반환 성공",
                examples=[
                    OpenApiExample(
                        name="성공 예시",
                        value={
                            "results": [
                                {
                                    "map_id": 26258,
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
        map_id = request.query_params.get("map_id")
        
        if map_id:
            foodmaps = FoodMap.objects.filter(map_id=map_id)
        else:
            foodmaps = FoodMap.objects.all()

        results = []
        for f in foodmaps:
            results.append({
                "map_id": f.map_id,
                "signature_menu": f.signature_menu
            })
        return Response({"results": results})