import json
import datetime
import jwt

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from .models import Users


# JWT 생성 함수
def create_jwt(user_id):
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


# 구글 토큰 검증 함수
def verify_google_token(id_token_str):
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception:
        return None


# 구글 로그인 API
@csrf_exempt
@require_POST
def google_login(request):
    try:
        body = json.loads(request.body)
        id_token_str = body.get("idToken")

        if not id_token_str:
            return JsonResponse({"message": "idToken required"}, status=400)

        # 토큰 검증
        user_info = verify_google_token(id_token_str)

        if not user_info:
            return JsonResponse({"message": "Invalid token"}, status=400)

        # 정보 추출
        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        #  유저 조회
        user = Users.objects.filter(google_id=google_id).first()

        #  없으면 회원가입
        if not user:
            user = Users.objects.create(
                email=email,
                nickname=name,
                profile_image=picture,
                google_id=google_id,
                status_cd="U001"  # ACTIVE 코드
            )

        # JWT 발급
        token = create_jwt(user.user_id)

        return JsonResponse({
            "message": "login success",
            "token": token,
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "nickname": user.nickname,
                "profile_image": user.profile_image
            }
        })

    except Exception as e:
        return JsonResponse({
            "message": "server error",
            "error": str(e)
        }, status=500)