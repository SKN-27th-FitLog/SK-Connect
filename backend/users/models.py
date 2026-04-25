from django.db import models

class Users(models.Model):

    #User 모델에 필드 추가
    ROLE_CHOICES = [("user", "일반사용자"), ("admin", "관리자")]

    user_id       = models.BigAutoField(primary_key=True)
    email         = models.CharField(unique=True, null=False, max_length=255)
    nickname      = models.CharField(max_length=100, blank=True, null=True)
    profile_image = models.CharField(max_length=255, blank=True, null=True)
    role          = models.CharField(max_length=10, choices=ROLE_CHOICES, default="user")  # 추가
    created_at    = models.DateTimeField(auto_now_add=True)
    status_cd     = models.ForeignKey('common.Codet', on_delete=models.DO_NOTHING, null=False, db_column='status_cd')

    class Meta:
        # managed = False  ← 제거
        db_table = 'users'

# 소셜 로그인 연동 계정 테이블(구글, 네이버, 카카오..)
class SocialAccount(models.Model):
    # 어떤 유저의 소셜 계정인지(User 테이블 참조)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='social_accounts')
    # 소셜 플랫폼 이름 
    provider = models.CharField(max_length=20)
    # 각 플랫폼에서 발급한 고유 사용자 ID
    provider_user_id = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'social_accounts'
        unique_together = ('provider', 'provider_user_id') # 같은 플랫폼에서 동일한 ID 중복 방지 

# Refresh Token 테이블
class RefreshToken(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE,related_name="refresh_tokens") # 토큰 소유 유저
    token = models.CharField(max_length=500, null=False, blank=False) # 실제 토큰 값
    ip_address = models.CharField(max_length=512, unique=True)  # 토큰 발급 시점의 IP 주소(의심 로그인 탐지용)
    user_agent = models.CharField(blank=True) # 토큰 발급 시점의 브라우저/기기 정보(의심 로그인 탐지용)
    is_revoked = models.BooleanField(default=False) # 토큰 폐기 여부(로그아웃 or 재발급 시 True로 변경)
    expires_at = models.DateTimeField() # 토큰 만료 시점
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "refresh_tokens"

# 의심 로그인 기록 테이블 
class SuspiciousLogin(models.Model):
    # 확인 대기 / 본인 확인 / 본인 아님
    STATUS = [("pending", "확인대기"), ("confirmed", "본인확인"), ("denied", "본인아님")]

    # 의심 로그인이 감지된 유저
    user = models.ForeignKey(Users, on_delete=models.CASCADE)
    # 의심 로그인 시도 IP
    ip_address = models.GenericIPAddressField()
    # 의심 로그인 시도 기기 정보
    user_agent = models.TextField()
    # 본인 확인 상태 (기본값: 확인 대기)
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "suspicious_logins"
