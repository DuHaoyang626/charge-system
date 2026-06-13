"""
管理端 — 配置管理路由
"""
from fastapi import APIRouter, Depends

from core.deps import get_current_admin
from core.response import resp_err, resp_ok
from service.admin.service import get_all_configs, update_configs

router = APIRouter(tags=["管理端-配置"])


@router.get("/admin/config")
async def admin_list_configs(admin_id: int = Depends(get_current_admin)):
    """获取全部配置。"""
    data = get_all_configs()
    return resp_ok(data=data)


@router.put("/admin/config")
async def admin_update_config(
    body: dict,
    admin_id: int = Depends(get_current_admin),
):
    """统一更新配置（只传需要修改的字段）。"""
    try:
        data = update_configs(body)
        return resp_ok(data=data, message="配置已更新")
    except Exception as e:
        return resp_err(400, str(e))
