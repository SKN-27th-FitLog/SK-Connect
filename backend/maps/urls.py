from django.urls import path
from .views import MapMarkersView, MapMarkerDetailView

urlpatterns = [
    # 전체 마커 조회 - GET /api/map/markers/
    path("markers/", MapMarkersView.as_view()),
    
    # 특정 마커 단건 조회 - GET /api/map/markers/{map_id}/
    path("markers/<int:map_id>/", MapMarkerDetailView.as_view()),
]