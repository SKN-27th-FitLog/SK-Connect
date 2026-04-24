from django.urls import path
from .views import social_login

urlpatterns = [
    path("auth/login/", social_login),  # 구글/네이버/카카오 통합 로그인 엔드포인트
]