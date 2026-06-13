"""
充电会话模块路由 — 发起、查询、换队、取消
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from core.database import engine as db_engine
from core.deps import get_current_user
from core.exceptions import AppException, Err
from core.response import resp_err, resp_ok
from model.protocol import Protocol
from model.session import ChargingSession
from model.station import Station
from model.user_protocol import UserProtocol
from service.dispatch.service import find_best_station
from service.queue.service import cancel_session, enqueue, move_to_station

router = APIRouter(tags=["充电会话"])


# ── 请求模型 ──


class CreateSessionRequest(BaseModel):
    requested_energy_kwh: float = Field(alias="requestedEnergyKwh", gt=0)
    protocol_ids: list[int] = Field(alias="protocolIds", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class SwitchStationRequest(BaseModel):
    target_station_id: int = Field(alias="targetStationId")

    model_config = ConfigDict(populate_by_name=True)


# ── 获取会话详情（内部复用） ──


def _build_session_detail(session: ChargingSession) -> dict:
    """构建会话详情响应。"""
    from sqlmodel import Session as DBSession
    with DBSession(db_engine) as db:
        station = db.get(Station, session.station_id)
        protocol = db.get(Protocol, session.protocol_id) if session.protocol_id else None
        now = datetime.utcnow()

        # 用户支持的协议
        up_rows = db.exec(
            select(UserProtocol, Protocol)
            .join(Protocol, UserProtocol.protocol_id == Protocol.id)
            .where(UserProtocol.user_id == session.user_id)
        ).all()
        supported_protocols = [
            {"id": p.id, "name": p.name, "powerKw": p.power_kw}
            for _, p in up_rows
        ]

        # 进度
        progress = 0
        if session.status == "charging" and session.requested_energy_kwh > 0:
            progress = min(100, int(session.charged_energy_kwh / session.requested_energy_kwh * 100))

        # 充电时长
        charging_duration = None
        if session.status == "charging" and session.started_charging_at:
            seconds = (now - session.started_charging_at).total_seconds()
            h, remainder = divmod(int(seconds), 3600)
            m, s = divmod(remainder, 60)
            charging_duration = f"{h:02d}:{m:02d}:{s:02d}"

        # 预计结束时间
        estimated_end = None
        if session.status == "charging" and session.started_charging_at and session.charged_energy_kwh > 0:
            elapsed = (now - session.started_charging_at).total_seconds()
            if elapsed > 0:
                rate = session.charged_energy_kwh / elapsed
                remaining_energy = session.requested_energy_kwh - session.charged_energy_kwh
                if rate > 0 and remaining_energy > 0:
                    remaining_sec = remaining_energy / rate
                    estimated_end = (now + timedelta(seconds=remaining_sec)).isoformat()

        # currentFee
        base_fee = station.base_service_fee if station else 5.0
        current_fee = {
            "electricityFee": session.charged_energy_kwh if session.status == "charging" else 0,
            "electricityDetails": [],
            "baseServiceFee": base_fee if session.zone in ("waiting", "charging") else 0,
            "timeServiceFee": 0,
            "totalServiceFee": base_fee if session.zone in ("waiting", "charging") else 0,
            "totalFee": (session.charged_energy_kwh if session.status == "charging" else 0)
                        + (base_fee if session.zone in ("waiting", "charging") else 0),
        }

        # bill
        bill = None
        if session.status in ("completed", "cancelled"):
            from model.bill import Bill as BillModel
            b = db.exec(
                select(BillModel).where(BillModel.session_id == session.id)
            ).first()
            if b:
                bill = {
                    "billId": b.id,
                    "totalFee": b.total_fee,
                    "paymentStatus": b.status,
                }

        return {
            "id": session.id,
            "status": session.status,
            "zone": session.zone,
            "station": {"id": station.id, "name": station.name} if station else None,
            "protocol": {
                "id": protocol.id,
                "name": protocol.name,
                "powerKw": protocol.power_kw,
            } if protocol else None,
            "requestedEnergyKwh": session.requested_energy_kwh,
            "chargedEnergyKwh": session.charged_energy_kwh,
            "progress": progress,
            "chargingDuration": charging_duration,
            "queuePosition": session.queue_position,
            "supportedProtocols": supported_protocols,
            "enteredQueueAt": session.created_at.isoformat() if session.created_at else None,
            "enteredWaitingAt": session.entered_waiting_at.isoformat() if session.entered_waiting_at else None,
            "startedChargingAt": session.started_charging_at.isoformat() if session.started_charging_at else None,
            "completedAt": session.completed_at.isoformat() if session.completed_at else None,
            "estimatedEndTime": estimated_end,
            "currentFee": current_fee,
            "bill": bill,
        }


# ── 路由 ──


@router.post("/sessions", status_code=201)
async def api_create_session(
    body: CreateSessionRequest,
    user_id: int = Depends(get_current_user),
):
    """发起充电请求。"""
    with Session(db_engine) as db:
        # 1. 校验用户没有进行中的会话
        active = db.exec(
            select(ChargingSession).where(
                ChargingSession.user_id == user_id,
                ChargingSession.status.in_(["queued", "waiting", "charging"]),
            )
        ).first()
        if active:
            return resp_err(409, "您已有进行中的充电会话，请先完成或取消")

        # 2. 校验协议在用户注册范围内
        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == user_id)
        ).all()
        user_protocol_ids = {up.protocol_id for up in up_rows}
        for pid in body.protocol_ids:
            if pid not in user_protocol_ids:
                return resp_err(400, f"协议 ID {pid} 不在您的支持范围内")

        # 3. 校验协议存在
        existing_protocols = db.exec(
            select(Protocol).where(Protocol.id.in_(body.protocol_ids))
        ).all()
        existing_ids = {p.id for p in existing_protocols}
        for pid in body.protocol_ids:
            if pid not in existing_ids:
                return resp_err(400, f"协议 ID {pid} 不存在")

    # 4. 计算最优桩（独立 session）
    best_station = find_best_station(user_id, body.protocol_ids)
    if best_station is None:
        return resp_err(400, "当前所有充电桩排队区已满，请稍后再试")

    # 5. 创建会话 + 入队（同一事务）
    with Session(db_engine) as db:
        session = ChargingSession(
            user_id=user_id,
            station_id=best_station.id,
            status="queued",
            zone="queue",
            requested_energy_kwh=body.requested_energy_kwh,
            charged_energy_kwh=0,
            queue_position=0,
        )
        db.add(session)
        db.flush()

        # 入队（共享 db session）
        position = enqueue(db, session, best_station)

        db.commit()
        db.refresh(session)

    wait_mins = _estimate_wait(best_station)

    return resp_ok(
        data={
            "sessionId": session.id,
            "status": "queued",
            "zone": "queue",
            "queuePosition": position,
            "station": {"id": best_station.id, "name": best_station.name},
            "requestedEnergyKwh": body.requested_energy_kwh,
            "estimatedWaitMinutes": wait_mins,
            "createdAt": session.created_at.isoformat() if session.created_at else None,
        },
        message="充电请求已提交，进入排队区",
        code=201,
        status_code=201,
    )


@router.get("/sessions/{session_id}")
async def api_get_session(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """获取充电会话详情。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None:
            raise AppException(*Err.NOT_FOUND)
        if session.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)

    return resp_ok(data=_build_session_detail(session))


@router.get("/sessions/{session_id}/switch-options")
async def api_get_switch_options(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """获取可换入的充电桩列表。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None:
            raise AppException(*Err.NOT_FOUND)
        if session.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)
        if session.status != "queued":
            return resp_ok(data={
                "sessionId": session_id,
                "currentStationId": session.station_id,
                "options": [],
            })

        current_station_id = session.station_id

        stations = db.exec(
            select(Station).where(
                Station.status == "running",
                Station.queue_count < Station.queue_capacity,
                Station.id != current_station_id,
            )
        ).all()

        options = [
            {"id": s.id, "name": s.name, "status": s.status}
            for s in stations
        ]

        return resp_ok(data={
            "sessionId": session_id,
            "currentStationId": current_station_id,
            "options": options,
        })


@router.post("/sessions/{session_id}/switch-station")
async def api_switch_station(
    session_id: int,
    body: SwitchStationRequest,
    user_id: int = Depends(get_current_user),
):
    """换到其他充电桩排队。"""
    result = move_to_station(session_id, body.target_station_id, user_id)
    return resp_ok(data=result, message="已更换到目标充电桩")


@router.post("/sessions/{session_id}/cancel")
async def api_cancel_session(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """取消充电请求。"""
    result = cancel_session(session_id, user_id)
    return resp_ok(data=result, message=result.get("message", "已取消"))


def _estimate_wait(station: Station) -> int:
    """预估等待时长（分钟）。"""
    total = station.queue_count + station.waiting_count
    if total == 0:
        return 0
    avg_charging_minutes = 30
    return total * avg_charging_minutes // (station.charging_capacity or 1)
