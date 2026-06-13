"""
管理端 — 充电桩管理（增删改 + 启动/停止/紧急停止）
"""

from fastapi import APIRouter, Depends

from core.deps import get_current_admin
from core.response import resp_err, resp_ok
from service.station.service import (
    create_station,
    delete_station,
    emergency_stop_station,
    start_station,
    stop_station,
    update_station,
)
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(tags=["管理端-充电桩"])


# ── 请求模型 ──


class CreateStationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    queue_capacity: int = Field(alias="queueCapacity", ge=1, default=5)
    waiting_capacity: int = Field(alias="waitingCapacity", ge=1, default=3)
    charging_capacity: int = Field(alias="chargingCapacity", ge=1, default=2)
    protocol_ids: list[int] = Field(alias="protocolIds", min_length=1)
    base_service_fee: float | None = Field(default=None, alias="baseServiceFee")

    model_config = ConfigDict(populate_by_name=True)


class UpdateStationRequest(BaseModel):
    name: str | None = None
    queue_capacity: int | None = Field(default=None, alias="queueCapacity", ge=1)
    waiting_capacity: int | None = Field(default=None, alias="waitingCapacity", ge=1)
    charging_capacity: int | None = Field(default=None, alias="chargingCapacity", ge=1)
    protocol_ids: list[int] | None = Field(default=None, alias="protocolIds")
    base_service_fee: float | None = Field(default=None, alias="baseServiceFee")

    model_config = ConfigDict(populate_by_name=True)


class EmergencyStopRequest(BaseModel):
    algorithm: str = "shortest_time_single"
    exclude_station_ids: list[int] | None = Field(default=None, alias="excludeStationIds")

    model_config = ConfigDict(populate_by_name=True)


# ── 路由 ──


@router.post("/admin/stations")
async def api_create_station(body: CreateStationRequest, admin_id: int = Depends(get_current_admin)):
    """创建充电桩。"""
    result = create_station(
        name=body.name,
        queue_capacity=body.queue_capacity,
        waiting_capacity=body.waiting_capacity,
        charging_capacity=body.charging_capacity,
        protocol_ids=body.protocol_ids,
        base_service_fee=body.base_service_fee,
    )
    return resp_ok(data=result, message="充电桩创建成功", code=201, status_code=201)


@router.put("/admin/stations/{station_id}")
async def api_update_station(
    station_id: int,
    body: UpdateStationRequest,
    admin_id: int = Depends(get_current_admin),
):
    """修改充电桩配置。"""
    # 过滤掉 None 字段，只传需要修改的
    data = body.model_dump(exclude_none=True, by_alias=False)
    # 转回 snake_case
    update_data = {}
    if "name" in data:
        update_data["name"] = data["name"]
    if "queue_capacity" in data:
        update_data["queue_capacity"] = data["queue_capacity"]
    if "waiting_capacity" in data:
        update_data["waiting_capacity"] = data["waiting_capacity"]
    if "charging_capacity" in data:
        update_data["charging_capacity"] = data["charging_capacity"]
    if "protocol_ids" in data:
        update_data["protocol_ids"] = data["protocol_ids"]
    if "base_service_fee" in data:
        update_data["base_service_fee"] = data["base_service_fee"]

    result = update_station(station_id, update_data)
    return resp_ok(data=result, message="充电桩配置已更新")


@router.delete("/admin/stations/{station_id}")
async def api_delete_station(station_id: int, admin_id: int = Depends(get_current_admin)):
    """删除充电桩（三个区域均无车辆时才能删除）。"""
    delete_station(station_id)
    return resp_ok(message="充电桩已删除")


@router.post("/admin/stations/{station_id}/start")
async def api_start_station(station_id: int, admin_id: int = Depends(get_current_admin)):
    """启动充电桩。"""
    result = start_station(station_id)
    return resp_ok(data=result, message="充电桩已启动")


@router.post("/admin/stations/{station_id}/stop")
async def api_stop_station(station_id: int, admin_id: int = Depends(get_current_admin)):
    """正常停止充电桩。"""
    result = stop_station(station_id)
    return resp_ok(data=result, message=result["message"])


@router.post("/admin/stations/{station_id}/emergency-stop")
async def api_emergency_stop(
    station_id: int,
    body: EmergencyStopRequest = EmergencyStopRequest(),
    admin_id: int = Depends(get_current_admin),
):
    """异常停止充电桩（重新调度排队/等待车辆）。"""
    result = emergency_stop_station(
        station_id,
        algorithm=body.algorithm,
        exclude_station_ids=body.exclude_station_ids,
    )
    return resp_ok(data=result, message=result["message"])
