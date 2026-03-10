from django.urls import path
from .views import MapMarkersView

urlpatterns = [
    path("markers", MapMarkersView.as_view()),
]