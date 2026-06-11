"""
管理端 — 报表统计路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-报表"])


@router.get("/admin/reports")
async def admin_reports():
    """报表统计（待实现）"""
    return {"message": "admin_reports - 待实现"}
