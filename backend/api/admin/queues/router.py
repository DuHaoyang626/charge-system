"""
管理端 — 排队队列管理路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-队列"])


@router.get("/admin/queues")
async def admin_list_queues():
    """队列概览（待实现）"""
    return {"message": "admin_list_queues - 待实现"}
