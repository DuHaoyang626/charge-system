"""
会话服务 — 会话详情构建、共享业务逻辑。
"""

from datetime import datetime, timedelta

from sqlmodel import Session as DBSession, select

from core.database import engine as db_engine
from model.bill import Bill
from model.config import ElectricityPrice, ServiceFeeTier
from model.protocol import Protocol
from model.session import ChargingSession
from model.station import Station
from model.user import User
from model.user_protocol import UserProtocol
from service.billing.engine import (
    PriceSlot, ServiceTier as BillingTier,
    calculate_electricity_fee, calculate_service_fee,
)

# 北京时间偏移（UTC+8）
BJT_OFFSET = timedelta(hours=8)


def _bjt_iso(dt: datetime | None) -> str | None:
    """将 UTC datetime 转为北京时间 ISO 字符串。"""
    if dt is None:
        return None
    return (dt + BJT_OFFSET).isoformat()


def build_session_detail(session: ChargingSession) -> dict:
    """
    构建会话详情响应（遵循 API 接口说明）。

    供用户端 GET /sessions/:id 和管理端 GET /admin/sessions/:id 共同使用。
    """
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
        elif session.status == "completed":
            progress = 100

        # 充电时长
        charging_duration = None
        if session.status == "charging" and session.started_charging_at:
            seconds = (now - session.started_charging_at).total_seconds()
            h, remainder = divmod(int(seconds), 3600)
            m, s = divmod(remainder, 60)
            charging_duration = f"{h:02d}:{m:02d}:{s:02d}"
        elif session.status == "completed" and session.started_charging_at and session.completed_at:
            seconds = (session.completed_at - session.started_charging_at).total_seconds()
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
                    estimated_end = _bjt_iso(now + timedelta(seconds=remaining_sec))

        # 实时费用 — 使用计费引擎计算
        base_fee = station.base_service_fee if station else 5.0
        current_fee = {
            "electricityFee": 0,
            "electricityDetails": [],
            "baseServiceFee": base_fee if session.zone in ("waiting", "charging") else 0,
            "timeServiceFee": 0,
            "totalServiceFee": base_fee if session.zone in ("waiting", "charging") else 0,
            "totalFee": base_fee if session.zone in ("waiting", "charging") else 0,
        }

        if session.status == "charging" and session.started_charging_at:
            # 加载电价时段和服务费阶梯配置
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

            # 充电时长（分钟）
            charging_seconds = (now - session.started_charging_at).total_seconds()
            charging_minutes = max(1, int(charging_seconds / 60))

            # 电费：按充电时段比例分摊已充电量
            if session.charged_energy_kwh > 0:
                elec_result = calculate_electricity_fee(
                    start_time=session.started_charging_at,
                    end_time=now,
                    total_energy_kwh=session.charged_energy_kwh,
                    prices=prices,
                )
                electricity_fee = elec_result.total
                electricity_details = [
                    {"period": item.name, "energy": item.quantity,
                     "price": item.unit_price, "fee": item.fee}
                    for item in elec_result.items
                ]
            else:
                electricity_fee = 0
                electricity_details = []

            # 服务费
            svc_result = calculate_service_fee(
                charging_minutes=charging_minutes,
                base_fee=base_fee,
                tiers=tiers,
            )
            time_service_fee = round(svc_result.total - base_fee, 2)
            total_service_fee = svc_result.total

            current_fee = {
                "electricityFee": electricity_fee,
                "electricityDetails": electricity_details,
                "baseServiceFee": base_fee,
                "timeServiceFee": time_service_fee,
                "totalServiceFee": total_service_fee,
                "totalFee": round(electricity_fee + total_service_fee, 2),
            }

        # 账单摘要
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


def get_session_user(session: ChargingSession) -> dict | None:
    """获取会话所属用户摘要。"""
    with DBSession(db_engine) as db:
        user = db.get(User, session.user_id)
        if user:
            return {"id": user.id, "licensePlate": user.license_plate}
        return None
