# users/utils/social.py

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings


def verify_google_token(id_token_str: str) -> dict | None:
    """
    구글 ID 토큰 검증
    - 성공 시 사용자 정보 반환 (sub, email, name, picture)
    - 실패 시 None 반환
    """
    try:
        idinfo = id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception:
        return None