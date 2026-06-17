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
from model.config import ElectricityPrice, ServiceFeeTier
from model.protocol import Protocol
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station, StationProtocol
from model.user_protocol import UserProtocol
from service.billing.engine import (
    PriceSlot, ServiceTier as BillingTier,
    calculate_electricity_fee, calculate_service_fee,
)
from service.dispatch.service import find_best_station
from service.queue.service import cancel_session, enqueue, move_to_station
from service.session.service import build_session_detail

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


# ── 获取会话详情 — 委托共享服务 ──


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
    return resp_ok(data=build_session_detail(session))


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
                "bill": None,
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
        if station.charging_count >= station.charging_capacity:
            return resp_err(400, f"充电区已满 ({station.charging_count}/{station.charging_capacity})")
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

        detail = build_session_detail(session)
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

                    # 使用数据库配置的分时电价计算预估费用
                    price_rows = db.exec(
                        select(ElectricityPrice).order_by(ElectricityPrice.start_time)
                    ).all()
                    prices = [
                        PriceSlot(period_name=r.period_name, start_time=r.start_time,
                                  end_time=r.end_time, price_per_kwh=r.price_per_kwh)
                        for r in price_rows
                    ]
                    tier_rows = db.exec(
                        select(ServiceFeeTier).order_by(ServiceFeeTier.min_minutes)
                    ).all()
                    tiers = [
                        BillingTier(tier_name=r.tier_name or f"{r.min_minutes}-{r.max_minutes or '∞'}分钟",
                                    min_minutes=r.min_minutes, max_minutes=r.max_minutes,
                                    rate_per_minute=r.rate_per_minute)
                        for r in tier_rows
                    ]

                    # 已充电部分按实际电价计算
                    charged_elec = calculate_electricity_fee(
                        start_time=session.started_charging_at,
                        end_time=now,
                        total_energy_kwh=session.charged_energy_kwh,
                        prices=prices,
                    )
                    # 剩余部分按当前时间到预计结束估算（按当前时段单一电价简化）
                    remaining_elec = calculate_electricity_fee(
                        start_time=now,
                        end_time=now + timedelta(seconds=remaining_sec),
                        total_energy_kwh=remaining,
                        prices=prices,
                    )
                    total_elec_fee = round(charged_elec.total + remaining_elec.total, 2)

                    # 服务费：按总预计充电时长估算
                    total_minutes = max(1, int((elapsed + remaining_sec) / 60))
                    base_fee = db.get(Station, session.station_id).base_service_fee if db.get(Station, session.station_id) else 5.0
                    svc_result = calculate_service_fee(
                        charging_minutes=total_minutes,
                        base_fee=base_fee,
                        tiers=tiers,
                    )

                    estimated_fee = round(total_elec_fee + svc_result.total, 2)

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
        detail = build_session_detail(fresh) if fresh else {}

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

        # 生成账单（使用计费引擎）
        from service.billing.engine import PriceSlot, ServiceTier, calculate_electricity_fee, calculate_service_fee
        from model.config import ElectricityPrice, ServiceFeeTier

        energy = session.charged_energy_kwh
        station_name = station.name if station else ""
        protocol_obj = db.get(Protocol, session.protocol_id) if session.protocol_id else None

        # 充电时长（分钟）
        now = datetime.utcnow()
        charging_minutes = 0
        if session.started_charging_at:
            seconds = (now - session.started_charging_at).total_seconds()
            charging_minutes = max(1, int(seconds / 60))

        # 电价时段
        price_rows = db.exec(
            select(ElectricityPrice).order_by(ElectricityPrice.start_time)
        ).all()
        prices = [
            PriceSlot(period_name=r.period_name, start_time=r.start_time,
                      end_time=r.end_time, price_per_kwh=r.price_per_kwh)
            for r in price_rows
        ]
        # 服务费阶梯
        tier_rows = db.exec(
            select(ServiceFeeTier).order_by(ServiceFeeTier.min_minutes)
        ).all()
        tiers = [
            ServiceTier(tier_name=r.tier_name or f"{r.min_minutes}-{r.max_minutes or '∞'}分钟",
                        min_minutes=r.min_minutes, max_minutes=r.max_minutes,
                        rate_per_minute=r.rate_per_minute)
            for r in tier_rows
        ]

        base_fee = station.base_service_fee if station else 5.0
        elec_result = calculate_electricity_fee(
            start_time=session.started_charging_at or now,
            end_time=now,
            total_energy_kwh=energy,
            prices=prices,
        )
        svc_result = calculate_service_fee(
            charging_minutes=charging_minutes,
            base_fee=base_fee,
            tiers=tiers,
        )

        electricity_fee = elec_result.total
        time_service_fee = round(svc_result.total - base_fee, 2)
        total_service_fee = svc_result.total

        # 构建分时电费明细
        electricity_details = [
            {
                "period": item.name,
                "energy": item.quantity,
                "price": item.unit_price,
                "fee": item.fee,
            }
            for item in elec_result.items
        ]

        bill = Bill(
            session_id=session.id, user_id=session.user_id,
            station_id=session.station_id,
            station_name=station_name,
            protocol_name=protocol_obj.name if protocol_obj else "",
            power_kw=protocol_obj.power_kw if protocol_obj else 0,
            total_energy_kwh=energy,
            electricity_fee=electricity_fee,
            base_service_fee=base_fee,
            time_service_fee=time_service_fee,
            service_fee=total_service_fee,
            total_fee=round(electricity_fee + total_service_fee, 2),
            charging_minutes=charging_minutes,
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
                    "electricityDetails": electricity_details,
                    "baseServiceFee": base_fee,
                    "timeServiceFee": time_service_fee,
                    "totalServiceFee": total_service_fee,
                    "totalFee": bill.total_fee,
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
