from django.urls import path
from .views import social_login, refresh_token_view

urlpatterns = [
    path("auth/login/", social_login),          # 소셜 로그인
    path("auth/token/refresh/", refresh_token_view),  # 토큰 재발급
]