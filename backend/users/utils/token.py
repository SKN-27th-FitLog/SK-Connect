import datetime
import jwt
from django.conf import settings

ACCESS_TOKEN_EXP = datetime.timedelta(minutes=30)
REFRESH_TOKEN_EXP = datetime.timedelta(days=14)


def create_access_token(user_id: int, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "type": "access",
        "exp": datetime.datetime.now(datetime.timezone.utc) + ACCESS_TOKEN_EXP,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "type": "refresh",
        "exp": datetime.datetime.now(datetime.timezone.utc) + REFRESH_TOKEN_EXP,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None