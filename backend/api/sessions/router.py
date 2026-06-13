"""
充电会话模块路由 — 发起、查询、换队、取消、确认、修改电量/协议、停止
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from core.database import engine as db_engine
from core.deps import get_current_user
from core.exceptions import AppException, Err
from core.response import resp_err, resp_ok
from model.bill import Bill
from model.protocol import Protocol
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station, StationProtocol
from model.user_protocol import UserProtocol
from service.dispatch.service import find_best_station
from service.queue.service import cancel_session, enqueue, move_to_station

router = APIRouter(tags=["充电会话"])

# 北京时间偏移（UTC+8），使前端直接显示正确北京时间
BJT_OFFSET = timedelta(hours=8)


def _bjt_iso(dt: datetime | None) -> str | None:
    """将 UTC datetime 转为北京时间 ISO 字符串（不加 Z/+08 标记，
    前端 new Date() 直接解析为本地时间即可显示正确值）。"""
    if dt is None:
        return None
    return (dt + BJT_OFFSET).isoformat()


# ── 请求模型 ──


class CreateSessionRequest(BaseModel):
    requested_energy_kwh: float = Field(alias="requestedEnergyKwh", gt=0)
    protocol_ids: list[int] = Field(alias="protocolIds", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


class SwitchStationRequest(BaseModel):
    target_station_id: int = Field(alias="targetStationId")

    model_config = ConfigDict(populate_by_name=True)


class ConfirmChargingRequest(BaseModel):
    action: str  # "confirm" | "reject"
    protocol_id: int | None = Field(default=None, alias="protocolId")
    requested_energy_kwh: float | None = Field(default=None, alias="requestedEnergyKwh", gt=0)

    model_config = ConfigDict(populate_by_name=True)


class UpdateEnergyRequest(BaseModel):
    requested_energy_kwh: float = Field(alias="requestedEnergyKwh", gt=0)

    model_config = ConfigDict(populate_by_name=True)


class UpdateProtocolRequest(BaseModel):
    protocol_ids: list[int] = Field(alias="protocolIds", min_length=1)

    model_config = ConfigDict(populate_by_name=True)


# ── 会话归属校验 ──


def _get_user_session(session_id: int, user_id: int) -> ChargingSession:
    """获取并校验会话属于当前用户。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None:
            raise AppException(*Err.NOT_FOUND)
        if session.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)
        return session


# ── 获取会话详情（内部复用） ──


def _build_session_detail(session: ChargingSession) -> dict:
    """构建会话详情响应。"""
    from sqlmodel import Session as DBSession
    with DBSession(db_engine) as db:
        station = db.get(Station, session.station_id)
        protocol = db.get(Protocol, session.protocol_id) if session.protocol_id else None
        now = datetime.utcnow()

        up_rows = db.exec(
            select(UserProtocol, Protocol)
            .join(Protocol, UserProtocol.protocol_id == Protocol.id)
            .where(UserProtocol.user_id == session.user_id)
        ).all()
        supported_protocols = [
            {"id": p.id, "name": p.name, "powerKw": p.power_kw}
            for _, p in up_rows
        ]

        progress = 0
        if session.status == "charging" and session.requested_energy_kwh > 0:
            progress = min(100, int(session.charged_energy_kwh / session.requested_energy_kwh * 100))

        charging_duration = None
        if session.status == "charging" and session.started_charging_at:
            seconds = (now - session.started_charging_at).total_seconds()
            h, remainder = divmod(int(seconds), 3600)
            m, s = divmod(remainder, 60)
            charging_duration = f"{h:02d}:{m:02d}:{s:02d}"

        estimated_end = None
        if session.status == "charging" and session.started_charging_at and session.charged_energy_kwh > 0:
            elapsed = (now - session.started_charging_at).total_seconds()
            if elapsed > 0:
                rate = session.charged_energy_kwh / elapsed
                remaining_energy = session.requested_energy_kwh - session.charged_energy_kwh
                if rate > 0 and remaining_energy > 0:
                    remaining_sec = remaining_energy / rate
                    estimated_end = _bjt_iso(now + timedelta(seconds=remaining_sec))

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

        bill = None
        if session.status in ("completed", "cancelled"):
            b = db.exec(
                select(Bill).where(Bill.session_id == session.id)
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
            "advanceReady": session.advance_ready,
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
            "enteredQueueAt": _bjt_iso(session.created_at),
            "enteredWaitingAt": _bjt_iso(session.entered_waiting_at),
            "startedChargingAt": _bjt_iso(session.started_charging_at),
            "completedAt": _bjt_iso(session.completed_at),
            "estimatedEndTime": estimated_end,
            "currentFee": current_fee,
            "bill": bill,
        }


# ── 原有路由 ──


@router.post("/sessions", status_code=201)
async def api_create_session(
    body: CreateSessionRequest,
    user_id: int = Depends(get_current_user),
):
    """发起充电请求。"""
    with Session(db_engine) as db:
        active = db.exec(
            select(ChargingSession).where(
                ChargingSession.user_id == user_id,
                ChargingSession.status.in_(["queued", "waiting", "charging"]),
            )
        ).first()
        if active:
            return resp_err(409, "您已有进行中的充电会话，请先完成或取消")

        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == user_id)
        ).all()
        user_protocol_ids = {up.protocol_id for up in up_rows}
        for pid in body.protocol_ids:
            if pid not in user_protocol_ids:
                return resp_err(400, f"协议 ID {pid} 不在您的支持范围内")

        existing_protocols = db.exec(
            select(Protocol).where(Protocol.id.in_(body.protocol_ids))
        ).all()
        existing_ids = {p.id for p in existing_protocols}
        for pid in body.protocol_ids:
            if pid not in existing_ids:
                return resp_err(400, f"协议 ID {pid} 不存在")

    best_station = find_best_station(user_id, body.protocol_ids)
    if best_station is None:
        return resp_err(400, "当前所有充电桩排队区已满，请稍后再试")

    with Session(db_engine) as db:
        session = ChargingSession(
            user_id=user_id,
            station_id=best_station.id,
            status="queued", zone="queue",
            requested_energy_kwh=body.requested_energy_kwh,
            charged_energy_kwh=0, queue_position=0,
        )
        db.add(session)
        db.flush()
        position = enqueue(db, session, best_station)
        db.commit()
        db.refresh(session)

    wait_mins = _estimate_wait(best_station)
    return resp_ok(
        data={
            "sessionId": session.id,
            "status": "queued", "zone": "queue",
            "queuePosition": position,
            "station": {"id": best_station.id, "name": best_station.name},
            "requestedEnergyKwh": body.requested_energy_kwh,
            "estimatedWaitMinutes": wait_mins,
            "createdAt": _bjt_iso(session.created_at),
        },
        message="充电请求已提交，进入排队区",
        code=201, status_code=201,
    )


@router.get("/sessions/{session_id}")
async def api_get_session(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """获取充电会话详情。"""
    _get_user_session(session_id, user_id)
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
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
        options = [{"id": s.id, "name": s.name, "status": s.status} for s in stations]
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


# ═══════════════════════════════════════════════
# 阶段 5：充电阶段操作
# ═══════════════════════════════════════════════


def _handle_reject(
    db: Session, session: ChargingSession, station: Station | None, body: ConfirmChargingRequest,
):
    """拒绝调度（排队态免费取消，等待态收基础服务费）。"""
    if session.status == "queued":
        # 排队态拒绝 → 免费取消
        if station:
            station.queue_count = max(0, station.queue_count - 1)
            db.add(station)
        session.status = "cancelled"
        session.zone = None
        session.cancelled_at = datetime.utcnow()
        session.queue_position = None
        session.advance_ready = False
        db.add(session)
        db.commit()

        return resp_ok(
            data={
                "sessionId": session.id, "status": "cancelled",
                "message": "已取消排队",
            },
            message="已取消排队",
        )

    # 等待态拒绝 → 收基础服务费取消
    if station:
        station.waiting_count = max(0, station.waiting_count - 1)
        db.add(station)

    base_fee = station.base_service_fee if station else 5.0
    session.status = "cancelled"
    session.zone = None
    session.cancelled_at = datetime.utcnow()
    session.queue_position = None
    session.advance_ready = False

    bill = Bill(
        session_id=session.id, user_id=session.user_id,
        station_id=session.station_id,
        station_name=station.name if station else "",
        total_fee=base_fee, electricity_fee=0,
        service_fee=base_fee, total_service_fee=base_fee,
        status="unpaid",
    )
    db.add(bill)
    db.add(session)
    db.commit()
    db.refresh(bill)

    return resp_ok(
        data={
            "sessionId": session.id, "status": "cancelled",
            "bill": {
                "billId": bill.id, "baseServiceFee": base_fee,
                "totalFee": base_fee, "paymentStatus": "unpaid",
            },
            "message": f"已取消，需支付基础服务费 ¥{base_fee:.2f}",
        },
        message=f"已取消，需支付基础服务费 ¥{base_fee:.2f}",
    )


def _handle_confirm(
    db: Session, session: ChargingSession, station: Station | None, body: ConfirmChargingRequest,
):
    """确认调度（排队→等待 / 等待→充电）。"""
    if not body.protocol_id:
        return resp_err(400, "请选择充电协议")

    protocol = db.get(Protocol, body.protocol_id)
    if protocol is None:
        return resp_err(400, "协议不存在")

    # 校验桩支持该协议
    sp = db.exec(
        select(StationProtocol).where(
            StationProtocol.station_id == session.station_id,
            StationProtocol.protocol_id == body.protocol_id,
        )
    ).first()
    if sp is None:
        return resp_err(400, "该充电桩不支持所选协议")

    if session.status == "queued":
        # ── 排队 → 等待 ──
        if station:
            station.queue_count = max(0, station.queue_count - 1)
            station.waiting_count += 1
            db.add(station)

        session.status = "waiting"
        session.zone = "waiting"
        session.entered_waiting_at = datetime.utcnow()
        session.queue_position = station.waiting_count if station else 1
        session.protocol_id = body.protocol_id
        session.advance_ready = False

        db.add(session)
        db.add(ScheduleLog(
            session_id=session.id,
            from_station_id=station.id if station else session.station_id,
            to_station_id=station.id if station else session.station_id,
            from_zone="queue", to_zone="waiting",
            triggered_by="user",
        ))
        db.commit()

        return resp_ok(
            data={
                "sessionId": session.id, "status": "waiting",
                "zone": "waiting",
                "protocol": {"id": protocol.id, "name": protocol.name, "powerKw": protocol.power_kw},
                "message": "已进入等待区",
            },
            message="已进入等待区",
        )

    # ── 等待 → 充电 ──
    if station:
        station.waiting_count = max(0, station.waiting_count - 1)
        station.charging_count += 1
        db.add(station)

    session.status = "charging"
    session.zone = "charging"
    session.protocol_id = body.protocol_id
    session.started_charging_at = datetime.utcnow()
    session.queue_position = None
    session.advance_ready = False

    if body.requested_energy_kwh is not None:
        session.requested_energy_kwh = body.requested_energy_kwh

    db.add(session)
    db.add(ScheduleLog(
        session_id=session.id,
        from_station_id=station.id if station else session.station_id,
        to_station_id=station.id if station else session.station_id,
        from_zone="waiting", to_zone="charging",
        triggered_by="user",
        detail=f"协议: {protocol.name} ({protocol.power_kw}kW)",
    ))
    db.commit()

    return resp_ok(
        data={
            "sessionId": session.id, "status": "charging",
            "protocol": {"id": protocol.id, "name": protocol.name, "powerKw": protocol.power_kw},
            "startedChargingAt": _bjt_iso(session.started_charging_at),
            "message": "开始充电",
        },
        message="开始充电",
    )


@router.post("/sessions/{session_id}/confirm-charging")
async def api_confirm_charging(
    session_id: int,
    body: ConfirmChargingRequest,
    user_id: int = Depends(get_current_user),
):
    """确认/拒绝调度（排队→等待 / 等待→充电）。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException(*Err.NOT_FOUND)
        if session.status not in ("queued", "waiting"):
            return resp_err(400, "当前状态不可确认充电")

        # 校验 advance_ready
        if not session.advance_ready:
            hint = "暂未就绪" if session.status == "queued" else "暂未调度到充电区"
            return resp_err(400, hint)

        station = db.get(Station, session.station_id)

        if body.action == "reject":
            return _handle_reject(db, session, station, body)

        # action == "confirm"
        return _handle_confirm(db, session, station, body)


@router.put("/sessions/{session_id}/energy")
async def api_update_energy(
    session_id: int,
    body: UpdateEnergyRequest,
    user_id: int = Depends(get_current_user),
):
    """修改目标电量。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException(*Err.NOT_FOUND)
        if session.status in ("completed", "cancelled"):
            raise AppException(*Err.SESSION_COMPLETED)

        if session.status == "charging":
            if body.requested_energy_kwh <= session.charged_energy_kwh:
                return resp_err(400, f"新电量必须大于已充电量 {session.charged_energy_kwh} kWh")

        session.requested_energy_kwh = body.requested_energy_kwh
        db.add(session)
        db.commit()

        detail = _build_session_detail(session)
        protocol = detail.get("protocol")

        now = datetime.utcnow()
        estimated_end = None
        estimated_fee = None
        if session.status == "charging" and session.started_charging_at and session.charged_energy_kwh > 0:
            elapsed = (now - session.started_charging_at).total_seconds()
            if elapsed > 0:
                rate = session.charged_energy_kwh / elapsed
                remaining = body.requested_energy_kwh - session.charged_energy_kwh
                if rate > 0 and remaining > 0:
                    remaining_sec = remaining / rate
                    estimated_end = _bjt_iso(now + timedelta(seconds=remaining_sec))
                    estimated_fee = round(remaining * 0.8 + session.charged_energy_kwh * 0.8 + 5.0, 2)

        return resp_ok(
        data={
            "sessionId": session.id,
            "requestedEnergyKwh": body.requested_energy_kwh,
            "chargedEnergyKwh": session.charged_energy_kwh,
            "protocol": protocol,
            "chargingDuration": detail.get("chargingDuration"),
            "currentFee": detail.get("currentFee"),
            "estimatedEndTime": estimated_end,
            "estimatedTotalFee": estimated_fee,
        },
        message="目标电量已更新",
    )


@router.get("/sessions/{session_id}/protocol-options")
async def api_protocol_options(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """获取候选充电协议。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException(*Err.NOT_FOUND)

        # 用户注册的协议
        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == user_id)
        ).all()
        user_ids = {up.protocol_id for up in up_rows}

        # 当前桩支持的协议
        sp_rows = db.exec(
            select(StationProtocol).where(StationProtocol.station_id == session.station_id)
        ).all()
        station_ids = {sp.protocol_id for sp in sp_rows}

        # 取交集（车辆支持 ∩ 充电桩支持）
        compatible_ids = user_ids & station_ids

        protocols = db.exec(
            select(Protocol).where(Protocol.id.in_(compatible_ids)).order_by(Protocol.power_kw.desc())
        ).all() if compatible_ids else []

        return resp_ok(data={
            "sessionId": session.id,
            "status": session.status,
            "selectedProtocolIds": [session.protocol_id] if session.protocol_id else [],
            "options": [
                {"id": p.id, "name": p.name, "powerKw": p.power_kw}
                for p in protocols
            ],
        })


@router.put("/sessions/{session_id}/protocol")
async def api_update_protocol(
    session_id: int,
    body: UpdateProtocolRequest,
    user_id: int = Depends(get_current_user),
):
    """修改支持的充电协议。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException(*Err.NOT_FOUND)
        if session.status in ("completed", "cancelled"):
            raise AppException(*Err.SESSION_COMPLETED)

        # 校验协议存在（充电态可以切换到其他协议，只要桩支持即可）
        for pid in body.protocol_ids:
            p = db.get(Protocol, pid)
            if p is None:
                return resp_err(400, f"协议 ID {pid} 不存在")

        # 充电态：校验在当前桩支持范围内
        if session.status == "charging":
            sp_rows = db.exec(
                select(StationProtocol).where(StationProtocol.station_id == session.station_id)
            ).all()
            station_ids = {sp.protocol_id for sp in sp_rows}
            for pid in body.protocol_ids:
                if pid not in station_ids:
                    return resp_err(400, f"协议 ID {pid} 不被当前充电桩支持")

        # 更新协议：充电态切换到用户选的协议，保留已有进度
        if session.status == "charging" and body.protocol_ids:
            new_pid = body.protocol_ids[0]
            if new_pid != session.protocol_id:
                session.protocol_id = new_pid
                # 不重置 started_charging_at，保留已充电量和时长
                db.add(session)

        db.commit()

    # 重新获取 session（避免 detached 问题）
    with Session(db_engine) as db2:
        fresh = db2.get(ChargingSession, session_id)
        detail = _build_session_detail(fresh) if fresh else {}

    return resp_ok(
        data={
            "sessionId": session_id,
            "supportedProtocols": detail.get("supportedProtocols", []),
            "chargedEnergyKwh": detail.get("chargedEnergyKwh", 0),
            "currentFee": detail.get("currentFee"),
        },
        message="充电协议已更新",
    )


@router.post("/sessions/{session_id}/stop-charging")
async def api_stop_charging(
    session_id: int,
    user_id: int = Depends(get_current_user),
):
    """结束充电。"""
    with Session(db_engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None or session.user_id != user_id:
            raise AppException(*Err.NOT_FOUND)
        if session.status != "charging":
            raise AppException(*Err.NOT_CHARGING)

        now = datetime.utcnow()
        session.status = "completed"
        session.zone = None
        session.completed_at = now

        # 充电桩计数
        station = db.get(Station, session.station_id)
        if station:
            station.charging_count = max(0, station.charging_count - 1)
            db.add(station)

        db.add(session)

        # 生成账单
        energy = session.charged_energy_kwh
        station_name = station.name if station else ""
        electricity_fee = round(energy * 0.8, 2)  # 简化电价 ¥0.8/kWh
        base_fee = station.base_service_fee if station else 5.0
        total_fee = round(electricity_fee + base_fee, 2)

        bill = Bill(
            session_id=session.id, user_id=session.user_id,
            station_id=session.station_id,
            station_name=station_name,
            protocol_name="",
            total_energy_kwh=energy,
            electricity_fee=electricity_fee,
            service_fee=base_fee,
            total_service_fee=base_fee,
            total_fee=total_fee,
            status="unpaid",
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        return resp_ok(
            data={
                "sessionId": session.id,
                "status": "completed",
                "chargedEnergyKwh": energy,
                "requestedEnergyKwh": session.requested_energy_kwh,
                "bill": {
                    "billId": bill.id,
                    "electricityFee": electricity_fee,
                    "baseServiceFee": base_fee,
                    "totalServiceFee": base_fee,
                    "totalFee": total_fee,
                    "paymentStatus": "unpaid",
                },
            },
            message="充电已结束",
        )


def _estimate_wait(station: Station) -> int:
    total = station.queue_count + station.waiting_count
    if total == 0:
        return 0
    avg_charging_minutes = 30
    return total * avg_charging_minutes // (station.charging_capacity or 1)
