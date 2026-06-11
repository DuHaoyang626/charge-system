"""
FastAPI 依赖注入 — 所有接口公用的依赖函数。

使用 Depends() 注入，无需在每个接口中重复校验逻辑。
"""

from fastapi import Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session

from core.database import engine
from core.security import verify_token
from core.exceptions import AppException, Err

# ──────────────────────────────────────────────
# 1. Token 解析
# ──────────────────────────────────────────────

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    从请求头 Authorization: Bearer <token> 中提取 user_id。
    所有需登录的接口都注入此依赖。
    """
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise AppException(*Err.UNAUTHORIZED)
    user_id = payload.get("user_id")
    if user_id is None:
        raise AppException(*Err.UNAUTHORIZED)
    return user_id


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> int:
    """
    管理员鉴权 — 比 get_current_user 多校验 role=admin。
    所有管理端接口都注入此依赖。
    """
    token = credentials.credentials
    payload = verify_token(token)
    if payload is None:
        raise AppException(*Err.UNAUTHORIZED)
    if payload.get("role") != "admin":
        raise AppException(*Err.FORBIDDEN)
    return payload.get("user_id")


# ──────────────────────────────────────────────
# 2. 数据库 Session
# ──────────────────────────────────────────────


def get_db() -> Session:
    """获取数据库 Session，每次请求独立，请求结束后自动关闭。"""
    with Session(engine) as session:
        yield session


# ──────────────────────────────────────────────
# 3. 分页参数
# ──────────────────────────────────────────────


def get_pagination(
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> tuple[int, int]:
    """
    统一提取分页参数。
    返回 (page, page_size)，接口中直接使用。
    """
    return page, page_size
