"""
充电桩模块路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["充电桩"])


@router.get("/stations")
async def list_stations():
    """充电桩列表（待实现）"""
    return {"message": "list_stations - 待实现"}


@router.get("/stations/{station_id}")
async def get_station(station_id: int):
    """充电桩详情（待实现）"""
    return {"message": f"get_station {station_id} - 待实现"}
