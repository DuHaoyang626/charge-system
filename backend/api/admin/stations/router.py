"""
管理端 — 充电桩管理路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["管理端-充电桩"])


@router.post("/admin/stations")
async def create_station():
    """创建充电桩（待实现）"""
    return {"message": "create_station - 待实现"}


@router.put("/admin/stations/{station_id}")
async def update_station(station_id: int):
    """更新充电桩（待实现）"""
    return {"message": f"update_station {station_id} - 待实现"}


@router.delete("/admin/stations/{station_id}")
async def delete_station(station_id: int):
    """删除充电桩（待实现）"""
    return {"message": f"delete_station {station_id} - 待实现"}


@router.put("/admin/stations/{station_id}/status")
async def set_station_status(station_id: int):
    """设置充电桩运行状态（待实现）"""
    return {"message": f"set_station_status {station_id} - 待实现"}
