"""
管理端 — 账单管理路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-账单"])


@router.get("/admin/bills")
async def admin_list_bills():
    """所有账单列表（待实现）"""
    return {"message": "admin_list_bills - 待实现"}
