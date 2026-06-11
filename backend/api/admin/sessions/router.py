"""
管理端 — 会话管理路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-会话"])


@router.get("/admin/sessions")
async def admin_list_sessions():
    """所有会话列表（待实现）"""
    return {"message": "admin_list_sessions - 待实现"}
