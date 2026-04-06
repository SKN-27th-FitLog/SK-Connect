# from rest_framework.views import APIView
# from rest_framework.response import Response
# from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
# from .models import FoodMap

# class FoodMapView(APIView):

#     @extend_schema(
#         summary="맛집 마커 조회",
#         description="지도에서 맛집 마커 클릭 시 해당 맛집의 시그니처 메뉴를 반환합니다.",
#         responses={
#             200: OpenApiResponse(
#                 description="맛집 마커 정보 반환 성공",
#                 examples=[
#                     OpenApiExample(
#                         name="성공 예시",
#                         value={
#                             "results": [
#                                 {
#                                     "map_id": 26258,
#                                     "signature_menu": "아메리카노"
#                                 }
#                             ]
#                         }
#                     )
#                 ]
#             )
#         }
#     )
#     def get(self, request):
#         # 쿼리 파라미터로 map_id 받기 (없으면 전체 조회)
#         map_id = request.query_params.get("map_id")
        
#         if map_id:
#             # 특정 맛집의 메뉴만 조회
#             foodmaps = FoodMap.objects.filter(map_id=map_id)
#         else:
#             # 전체 맛집 메뉴 조회
#             foodmaps = FoodMap.objects.all()

#         results = []
#         for f in foodmaps:
#             results.append({
#                 "map_id": f.map_id, # 장소 id
#                 "signature_menu": f.signature_menu # 시그니처 메뉴
#             })
#         return Response({"results": results})

from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample
from .models import FoodMap
from .serializers import FoodMapSerializer

# 전체 조회 + 조건 조회 API
class FoodMapView(APIView):

    @extend_schema(
        summary="맛집 시그니처 메뉴 조회",
        description="map_id로 특정 맛집의 시그니처 메뉴를 조회합니다. map_id 없으면 전체 반환.",
        responses={
            200: OpenApiResponse(description="시그니처 메뉴 반환 성공")
        }
    )
    def get(self, request):
        # 쿼리 파라미터로 map_id 받기 (없으면 전체 조회)
        map_id = request.query_params.get("map_id")

        if map_id:
            # 특정 맛집의 메뉴만 조회
            foodmaps = FoodMap.objects.filter(map_id=map_id)
        else:
            # 전체 맛집 메뉴 조회
            foodmaps = FoodMap.objects.all()

            # 조회된 데이터를 JSON 형태로 변환
        serializer = FoodMapSerializer(foodmaps, many=True)
        return Response({"results": serializer.data})

# 특정 맛집 상세 조회 API
class FoodMapDetailView(APIView):

    @extend_schema(
        summary="특정 맛집 시그니처 메뉴 조회",
        description="map_id로 특정 맛집의 시그니처 메뉴를 반환합니다.",
        responses={
            200: OpenApiResponse(description="시그니처 메뉴 반환 성공")
        }
    )
    def get(self, request, map_id):
        foodmaps = FoodMap.objects.filter(map_id=map_id)
        if not foodmaps.exists():
            return Response({"error": "해당 맛집을 찾을 수 없습니다."}, status=404)
        
        serializer = FoodMapSerializer(foodmaps, many=True)
        return Response({"results": serializer.data})