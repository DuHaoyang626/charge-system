"""
管理端 — 配置管理路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-配置"])


@router.get("/admin/config")
async def list_configs():
    """配置列表（待实现）"""
    return {"message": "list_configs - 待实现"}


@router.put("/admin/config")
async def update_config():
    """更新配置（待实现）"""
    return {"message": "update_config - 待实现"}
