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
# 로그인 성공 시 사용자 식별용 토큰 발급
def create_jwt(user_id):
    payload = {
        "user_id": user_id,  # 사용자 고유 ID
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)  # 토큰 만료시간 (1시간)
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    return token


# 구글 ID 토큰 검증 함수
# 프론트에서 받은 idToken을 구글 서버 기준으로 검증
def verify_google_token(id_token_str):
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID  # 구글 클라이언트 ID
        )
        return idinfo  # 검증 성공 시 사용자 정보 반환
    except Exception:
        return None  # 실패 시 None 반환


# 구글 로그인 API
# 프론트에서 idToken 받아 로그인 처리
@csrf_exempt  # CSRF 검사 비활성화 (API 테스트용)
@require_POST  # POST 요청만 허용
def google_login(request):
    try:
        # 요청 body(JSON) 파싱
        body = json.loads(request.body)
        id_token_str = body.get("idToken")

        # idToken이 없으면 에러
        if not id_token_str:
            return JsonResponse({"message": "idToken required"}, status=400)

        # 테스트용 분기 (프론트 없이 로그인 테스트용)
        if id_token_str == "test-success":
            user_info = {
                "sub": "test_google_id_456",  # 구글 고유 ID
                "email": "test2@example.com",
                "name": "테스트유저2",
                "picture": ""
            }
        else:
            # 실제 구글 토큰 검증
            user_info = verify_google_token(id_token_str)

        # 토큰 검증 실패 시
        if not user_info:
            return JsonResponse({"message": "Invalid token"}, status=400)

        # 구글 사용자 정보 추출
        google_id = user_info.get("sub")
        email = user_info.get("email")
        name = user_info.get("name")
        picture = user_info.get("picture")

        # 기존 사용자 조회 (google_id 기준)
        user = Users.objects.filter(google_id=google_id).first()

        # 사용자가 없으면 회원가입
        if not user:
            user = Users.objects.create(
                email=email,
                nickname=name,
                profile_image=picture,
                google_id=google_id,
                status_cd_id="US01"  # 사용자 상태 (활성)
            )

        # JWT 토큰 발급
        token = create_jwt(user.user_id)

        # 로그인 성공 응답 반환
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
        # 서버 내부 에러 처리
        return JsonResponse({
            "message": "server error",
            "error": str(e)
        }, status=500)