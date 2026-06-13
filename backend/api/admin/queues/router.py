"""
管理端 — 排队队列管理路由
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field

from core.deps import get_current_admin
from core.response import resp_err, resp_ok
from service.queue.admin_service import (
    list_all_queues,
    move_session_to_station,
    reorder_queue,
)

router = APIRouter(tags=["管理端-队列"])


class ReorderRequest(BaseModel):
    station_id: int = Field(alias="stationId")
    zone: str  # "queue" | "waiting"
    session_id: int = Field(alias="sessionId")
    new_position: int = Field(alias="newPosition", ge=1)

    model_config = ConfigDict(populate_by_name=True)


class MoveRequest(BaseModel):
    session_id: int = Field(alias="sessionId")
    target_station_id: int = Field(alias="targetStationId")
    target_position: int | None = Field(default=None, alias="targetPosition", ge=1)

    model_config = ConfigDict(populate_by_name=True)


@router.get("/admin/queues")
async def admin_list_queues(admin_id: int = Depends(get_current_admin)):
    """查看所有充电桩的三区队列。"""
    data = list_all_queues()
    return resp_ok(data=data)


@router.put("/admin/queues/reorder")
async def admin_reorder_queue(
    body: ReorderRequest,
    admin_id: int = Depends(get_current_admin),
):
    """修改队列位置。"""
    try:
        result = reorder_queue(
            station_id=body.station_id,
            zone=body.zone,
            session_id=body.session_id,
            new_position=body.new_position,
        )
        return resp_ok(data=result, message="队列位置已更新")
    except Exception as e:
        return resp_err(400, str(e))


@router.put("/admin/queues/move")
async def admin_move_session(
    body: MoveRequest,
    admin_id: int = Depends(get_current_admin),
):
    """将车辆移动到其他充电桩。"""
    try:
        result = move_session_to_station(
            session_id=body.session_id,
            target_station_id=body.target_station_id,
            target_position=body.target_position,
        )
        return resp_ok(data=result, message="车辆已移动到目标桩")
    except Exception as e:
        return resp_err(400, str(e))
