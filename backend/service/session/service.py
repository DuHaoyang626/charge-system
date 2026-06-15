"""
会话服务 — 会话详情构建、共享业务逻辑。
"""

from datetime import datetime, timedelta

from sqlmodel import Session as DBSession, select

from core.database import engine as db_engine
from model.bill import Bill
from model.protocol import Protocol
from model.session import ChargingSession
from model.station import Station
from model.user import User
from model.user_protocol import UserProtocol

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

        # 实时费用
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
