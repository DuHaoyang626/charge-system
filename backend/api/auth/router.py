"""
认证模块路由占位 — 注册 / 登录 / 用户信息
"""

from fastapi import APIRouter

router = APIRouter(tags=["认证"])


@router.post("/auth/register")
async def register():
    """用户注册（待实现）"""
    return {"message": "register - 待实现"}


@router.post("/auth/login")
async def login():
    """用户登录（待实现）"""
    return {"message": "login - 待实现"}
