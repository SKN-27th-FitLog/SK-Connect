import json
import logging
import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# 필요한 모델 import
from .models import Users, SocialAccount, RefreshToken, SuspiciousLogin
# 토큰 유틸리티 import
from .utils.token import create_access_token, create_refresh_token, REFRESH_TOKEN_EXP
# 소셜 토큰 검증 함수 import
from .utils.social import verify_google_token

logger = logging.getLogger(__name__)


def get_client_ip(request) -> str:
    """
    요청자 IP 추출
    - 프록시 서버를 거친 경우 HTTP_X_FORWARDED_FOR 헤더에서 추출
    - 직접 요청인 경우 REMOTE_ADDR에서 추출
    """
    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    return x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")


def is_suspicious(user: Users, ip: str, user_agent: str) -> bool:
    """
    의심 로그인 판단
    - 이전 로그인 기록과 IP, 기기 정보가 모두 다르면 의심으로 판단
    - 첫 로그인은 비교할 기록이 없으므로 의심하지 않음
    """
    # 가장 최근 Refresh Token 기록 조회
    previous = RefreshToken.objects.filter(user=user).order_by("-created_at").first()
    if not previous:
        return False  # 첫 로그인이면 의심 아님
    # IP와 기기가 모두 다를 때만 의심으로 판단
    return previous.ip_address != ip and previous.user_agent != user_agent


@csrf_exempt  # CSRF 검사 비활성화 (JWT 기반 인증이라 불필요)
@require_POST  # POST 요청만 허용
def social_login(request):
    try:
        # 요청 body(JSON) 파싱
        body         = json.loads(request.body)
        provider     = body.get("provider")    # 소셜 플랫폼 종류 "google" | "naver" | "kakao"
        id_token_str = body.get("idToken")     # 소셜 플랫폼에서 받은 토큰

        # provider, idToken 둘 다 필수
        if not provider or not id_token_str:
            return JsonResponse({"message": "provider, idToken 필수입니다"}, status=400)

        # ── 소셜 토큰 검증 ──────────────────────────────
        # provider에 따라 다른 검증 함수 호출
        # 나중에 네이버/카카오 추가 시 elif로 확장
        if provider == "google":
            user_info = verify_google_token(id_token_str)
            # 테스트용 분기 (프론트 없이 테스트할 때만 사용, 배포 전 삭제)
            if id_token_str == "test-success":
                user_info = {
                    "sub": "test_google_id_123",
                    "email": "test@example.com",
                    "name": "테스트유저",
                    "picture": None
                }
            else:
                user_info = verify_google_token(id_token_str)
        else:
            return JsonResponse({"message": f"지원하지 않는 provider: {provider}"}, status=400)

        # 토큰 검증 실패 시
        if not user_info:
            return JsonResponse({"message": "유효하지 않은 소셜 토큰"}, status=401)

        # ── 사용자 정보 추출 ─────────────────────────────
        provider_user_id = user_info.get("sub")           # 소셜 플랫폼의 고유 사용자 ID
        email            = user_info.get("email")
        name             = user_info.get("name", "")
        picture          = user_info.get("picture") or None  # 없으면 None으로 저장

        # sub, email 둘 다 없으면 처리 불가
        if not provider_user_id or not email:
            return JsonResponse({"message": "토큰 페이로드 불완전"}, status=400)

        # ── 사용자 조회 / 생성 ───────────────────────────
        # SocialAccount 테이블에서 기존 소셜 계정 조회
        social = SocialAccount.objects.filter(
            provider=provider,
            provider_user_id=provider_user_id
        ).select_related("user").first()

        if social:
            # 기존 회원 - 이메일 · 프로필 변경사항 업데이트
            user = social.user
            updated = False
            if user.email != email:
                user.email = email
                updated = True
            if picture and user.profile_image != picture:
                user.profile_image = picture
                updated = True
            if updated:
                user.save()
        else:
            # 신규 회원 - Users 테이블에 유저 생성 후 SocialAccount 연결
            user = Users.objects.create(
                email=email,
                nickname=name,
                profile_image=picture,
                status_cd_id="US01",  # 활성 상태
                role="user",          # 기본 권한
            )
            SocialAccount.objects.create(
                user=user,
                provider=provider,
                provider_user_id=provider_user_id,
            )

        # ── 의심 로그인 탐지 ─────────────────────────────
        ip         = get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")  # 브라우저/기기 정보
        suspicious = is_suspicious(user, ip, user_agent)

        if suspicious:
            # 의심 로그인 기록 저장 (나중에 이메일 알림 등에 활용)
            SuspiciousLogin.objects.create(user=user, ip_address=ip, user_agent=user_agent)

        # ── 토큰 발급 ────────────────────────────────────
        access_token  = create_access_token(user.user_id, user.role)   # 인증용 (30분)
        refresh_token = create_refresh_token(user.user_id)              # 재발급용 (14일)

        # Refresh Token DB 저장 (IP, 기기 정보 함께 저장)
        RefreshToken.objects.create(
            user=user,
            token=refresh_token,
            ip_address=ip,
            user_agent=user_agent,
            expires_at=datetime.datetime.now(datetime.timezone.utc) + REFRESH_TOKEN_EXP,
        )

        # ── 응답 반환 ────────────────────────────────────
        return JsonResponse({
            "message":       "login success",
            "access_token":  access_token,
            "refresh_token": refresh_token,
            "suspicious":    suspicious,   # 프론트에서 의심 로그인 안내 모달 표시용
            "user": {
                "user_id":       user.user_id,
                "email":         user.email,
                "nickname":      user.nickname,
                "profile_image": user.profile_image,
                "role":          user.role,
            }
        })

    except json.JSONDecodeError:
        # JSON 파싱 실패
        return JsonResponse({"message": "잘못된 JSON 형식"}, status=400)
    except Exception:
        # 예상치 못한 서버 에러 - 스택 트레이스 로그 기록
        logger.exception("social_login error")
        return JsonResponse({"message": "서버 오류"}, status=500)