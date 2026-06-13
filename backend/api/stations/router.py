"""
充电桩模块路由（用户端）— 列表 & 详情
"""

from fastapi import APIRouter, Depends

from core.deps import get_current_user
from core.response import resp_err, resp_ok
from service.station.service import get_station_detail, list_stations

router = APIRouter(tags=["充电桩"])


@router.get("/stations")
async def api_list_stations(user_id: int = Depends(get_current_user)):
    """获取所有充电桩列表（含状态、容量、支持的协议）。"""
    result = list_stations()
    return resp_ok(data=result)


@router.get("/stations/{station_id}")
async def api_get_station(station_id: int, user_id: int = Depends(get_current_user)):
    """获取单个充电桩详情（含三区车辆列表）。"""
    result = get_station_detail(station_id)
    return resp_ok(data=result)
