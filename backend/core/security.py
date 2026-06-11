"""
JWT 签发与验签 + 密码哈希。

Token Payload:
    {
        "user_id": 1,
        "role": "user",
        "exp": 1778515200,
        "iat": 1778428800
    }
"""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from core.config import settings

# ── JWT ──

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_access_token(user_id: int, role: str = "user") -> str:
    """签发 JWT Token，有效期 24 小时。"""
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": int((datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)).timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """验证 Token，成功返回 payload dict，失败返回 None。"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# ── 密码哈希 ──


def get_password_hash(password: str) -> str:
    """对明文密码进行 bcrypt 哈希。"""
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """校验明文密码与哈希值是否匹配。"""
    return _pwd_ctx.verify(plain_password, hashed_password)
