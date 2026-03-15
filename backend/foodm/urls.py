from django.urls import path
from .views import FoodMapView

urlpatterns = [
    path("", FoodMapView.as_view()),
]