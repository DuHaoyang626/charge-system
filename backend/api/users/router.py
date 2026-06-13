"""
用户模块路由 — 获取当前用户信息
"""

from fastapi import APIRouter, Depends

from core.deps import get_current_user
from core.response import resp_ok
from service.account.service import get_user_info

router = APIRouter(tags=["用户"])


@router.get("/users/me")
async def api_get_user_me(user_id: int = Depends(get_current_user)):
    """获取当前登录用户的完整信息。"""
    result = get_user_info(user_id)
    return resp_ok(data=result)
