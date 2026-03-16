from django.urls import path
from .views import FoodMapView, FoodMapDetailView

urlpatterns = [
    # 전체 조회 - GET /api/foodmap/
    path("", FoodMapView.as_view()),
    # 특정 맛집 조회 - GET /api/foodmap/{map_id}/
    path("<int:map_id>/", FoodMapDetailView.as_view()),
]