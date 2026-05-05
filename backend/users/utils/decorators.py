from functools import wraps
from django.http import JsonResponse
from .token import decode_token


def login_required(f):
    """
    로그인 여부 확인 데코레이터
    - Authorization 헤더에서 Access Token 추출
    - 유효한 토큰이면 통과, 아니면 401 반환
    - 통과하면 request에 user_id, role 저장
    """
    @wraps(f)
    def wrapper(request, *args, **kwargs):
        # Authorization 헤더 확인
        auth = request.headers.get("Authorization", "")

        # "Bearer 토큰" 형식인지 확인
        if not auth.startswith("Bearer "):
            return JsonResponse({"message": "토큰이 없습니다"}, status=401)

        # 토큰 검증
        payload = decode_token(auth.split(" ")[1])
        if not payload or payload.get("type") != "access":
            return JsonResponse({"message": "유효하지 않은 토큰입니다"}, status=401)

        # 이후 뷰에서 user_id, role 사용할 수 있도록 저장
        request.user_id = payload["user_id"]
        request.role    = payload["role"]
        return f(request, *args, **kwargs)
    return wrapper


def admin_required(f):
    """
    관리자 권한 확인 데코레이터
    - login_required 통과 후 role이 admin인지 확인
    - admin이 아니면 403 반환
    """
    @wraps(f)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.role != "admin":
            return JsonResponse({"message": "관리자 권한이 필요합니다"}, status=403)
        return f(request, *args, **kwargs)
    return wrapper