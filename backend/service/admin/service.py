"""
管理端服务 — 配置管理、会话管理、账单管理、报表统计。
"""
import logging
from datetime import datetime, timedelta, date

from sqlmodel import Session, select, func

from core.database import engine
from core.exceptions import AppException
from model.bill import Bill
from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
from model.session import ChargingSession
from model.station import Station
from model.user import User
from model.user_protocol import UserProtocol
from model.protocol import Protocol
from model.schedule_log import ScheduleLog

logger = logging.getLogger("charge-system.admin")

BJT_OFFSET = timedelta(hours=8)


# ═══════════════════════════════════════════
# 配置管理
# ═══════════════════════════════════════════

def get_all_configs() -> dict:
    """获取全部配置。"""
    with Session(engine) as db:
        configs = db.exec(select(GlobalConfig)).all()
        prices = db.exec(
            select(ElectricityPrice).order_by(ElectricityPrice.start_time)
        ).all()
        tiers = db.exec(
            select(ServiceFeeTier).order_by(ServiceFeeTier.min_minutes)
        ).all()

        return {
            "globalConfigs": {
                c.config_key: c.config_value for c in configs
            },
            "electricityPrices": [
                {
                    "id": p.id,
                    "periodName": p.period_name,
                    "startTime": p.start_time,
                    "endTime": p.end_time,
                    "pricePerKwh": p.price_per_kwh,
                    "priority": p.priority,
                }
                for p in prices
            ],
            "serviceFeeTiers": [
                {
                    "id": t.id,
                    "tierName": t.tier_name or f"{t.min_minutes}-{t.max_minutes or '∞'}分钟",
                    "minMinutes": t.min_minutes,
                    "maxMinutes": t.max_minutes,
                    "ratePerMinute": t.rate_per_minute,
                }
                for t in tiers
            ],
        }


def update_configs(data: dict) -> dict:
    """统一更新配置。"""
    with Session(engine) as db:
        now = datetime.utcnow()

        # 更新全局键值配置
        if "globalConfigs" in data:
            for key, value in data["globalConfigs"].items():
                existing = db.exec(
                    select(GlobalConfig).where(GlobalConfig.config_key == key)
                ).first()
                if existing:
                    existing.config_value = str(value)
                    existing.updated_at = now
                    db.add(existing)

        # 更新电价
        if "electricityPrices" in data:
            for item in data["electricityPrices"]:
                pid = item.get("id")
                if pid:
                    p = db.get(ElectricityPrice, pid)
                    if p:
                        if "periodName" in item:
                            p.period_name = item["periodName"]
                        if "startTime" in item:
                            p.start_time = item["startTime"]
                        if "endTime" in item:
                            p.end_time = item["endTime"]
                        if "pricePerKwh" in item:
                            p.price_per_kwh = item["pricePerKwh"]
                        if "priority" in item:
                            p.priority = item["priority"]
                        db.add(p)

        # 更新服务费阶梯
        if "serviceFeeTiers" in data:
            for item in data["serviceFeeTiers"]:
                tid = item.get("id")
                if tid:
                    t = db.get(ServiceFeeTier, tid)
                    if t:
                        if "tierName" in item:
                            t.tier_name = item["tierName"]
                        if "minMinutes" in item:
                            t.min_minutes = item["minMinutes"]
                        if "maxMinutes" in item:
                            t.max_minutes = item["maxMinutes"]
                        if "ratePerMinute" in item:
                            t.rate_per_minute = item["ratePerMinute"]
                        db.add(t)

        db.commit()

    return get_all_configs()


# ═══════════════════════════════════════════
# 会话管理
# ═══════════════════════════════════════════

def list_all_sessions(
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    station_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """查看所有用户会话（分页）。"""
    with Session(engine) as db:
        query = select(ChargingSession)
        if status:
            query = query.where(ChargingSession.status == status)
        if station_id:
            query = query.where(ChargingSession.station_id == station_id)
        if user_id:
            query = query.where(ChargingSession.user_id == user_id)

        total = db.exec(select(func.count()).select_from(query.subquery())).one()

        query = query.order_by(ChargingSession.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = db.exec(query).all()

        result = []
        for s in rows:
            user = db.get(User, s.user_id)
            station = db.get(Station, s.station_id)
            result.append({
                "id": s.id,
                "userId": s.user_id,
                "licensePlate": user.license_plate if user else "未知",
                "stationId": s.station_id,
                "stationName": station.name if station else "未知",
                "status": s.status,
                "zone": s.zone,
                "requestedEnergyKwh": s.requested_energy_kwh,
                "chargedEnergyKwh": s.charged_energy_kwh,
                "advanceReady": s.advance_ready,
                "createdAt": _bjt_iso(s.created_at),
            })

        return {"list": result, "page": page, "pageSize": page_size, "total": total}


def get_admin_session_detail(session_id: int) -> dict | None:
    """查看任意会话详情。"""
    with Session(engine) as db:
        s = db.get(ChargingSession, session_id)
        if s is None:
            return None
        user = db.get(User, s.user_id)
        station = db.get(Station, s.station_id)
        protocol = db.get(Protocol, s.protocol_id) if s.protocol_id else None

        return {
            "id": s.id,
            "userId": s.user_id,
            "licensePlate": user.license_plate if user else "未知",
            "userName": user.user_name if user else "",
            "stationId": s.station_id,
            "stationName": station.name if station else "未知",
            "protocol": {
                "id": protocol.id, "name": protocol.name, "powerKw": protocol.power_kw
            } if protocol else None,
            "status": s.status,
            "zone": s.zone,
            "advanceReady": s.advance_ready,
            "requestedEnergyKwh": s.requested_energy_kwh,
            "chargedEnergyKwh": s.charged_energy_kwh,
            "queuePosition": s.queue_position,
            "createdAt": _bjt_iso(s.created_at),
            "enteredWaitingAt": _bjt_iso(s.entered_waiting_at),
            "startedChargingAt": _bjt_iso(s.started_charging_at),
            "completedAt": _bjt_iso(s.completed_at),
        }


# ═══════════════════════════════════════════
# 账单管理
# ═══════════════════════════════════════════

def list_all_bills(
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    station_id: int | None = None,
    payment_status: str | None = None,
) -> dict:
    """查看所有账单（分页）。"""
    with Session(engine) as db:
        query = select(Bill)
        if user_id:
            query = query.where(Bill.user_id == user_id)
        if station_id:
            query = query.where(Bill.station_id == station_id)
        if payment_status:
            query = query.where(Bill.status == payment_status)

        total = db.exec(select(func.count()).select_from(query.subquery())).one()
        query = query.order_by(Bill.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = db.exec(query).all()

        result = []
        for b in rows:
            user = db.get(User, b.user_id)
            result.append({
                "billId": b.id,
                "sessionId": b.session_id,
                "userId": b.user_id,
                "licensePlate": user.license_plate if user else "未知",
                "stationName": b.station_name,
                "totalFee": b.total_fee,
                "electricityFee": b.electricity_fee,
                "serviceFee": b.service_fee,
                "totalEnergyKwh": b.total_energy_kwh,
                "paymentStatus": b.status,
                "createdAt": _bjt_iso(b.created_at),
                "paidAt": _bjt_iso(b.paid_at),
            })

        return {"list": result, "page": page, "pageSize": page_size, "total": total}


def get_admin_bill_detail(bill_id: int) -> dict | None:
    """查看任意账单详情。"""
    from service.billing.service import get_bill
    return get_bill(bill_id, user_id=None)


# ═══════════════════════════════════════════
# 报表统计
# ═══════════════════════════════════════════

def get_charging_volume_report(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """充电量统计。"""
    with Session(engine) as db:
        query = select(Bill).where(Bill.status == "paid")
        if start_date:
            sd = date.fromisoformat(start_date)
            query = query.where(Bill.created_at >= datetime(sd.year, sd.month, sd.day))
        if end_date:
            ed = date.fromisoformat(end_date)
            query = query.where(
                Bill.created_at < datetime(ed.year, ed.month, ed.day) + timedelta(days=1)
            )

        bills = db.exec(query).all()
        total_energy = sum(b.total_energy_kwh for b in bills)
        total_revenue = sum(b.total_fee for b in bills)
        count = len(bills)

        # 按站统计
        station_stats: dict[int, dict] = {}
        for b in bills:
            if b.station_id not in station_stats:
                st = db.get(Station, b.station_id)
                station_stats[b.station_id] = {
                    "stationId": b.station_id,
                    "stationName": st.name if st else "未知",
                    "totalEnergy": 0,
                    "totalRevenue": 0,
                    "count": 0,
                }
            station_stats[b.station_id]["totalEnergy"] += b.total_energy_kwh
            station_stats[b.station_id]["totalRevenue"] += b.total_fee
            station_stats[b.station_id]["count"] += 1

        return {
            "summary": {
                "totalEnergy": round(total_energy, 2),
                "totalRevenue": round(total_revenue, 2),
                "totalSessions": count,
            },
            "byStation": [
                {"stationName": v["stationName"], "totalEnergy": round(v["totalEnergy"], 2),
                 "totalRevenue": round(v["totalRevenue"], 2), "count": v["count"]}
                for v in station_stats.values()
            ],
        }


def get_revenue_report(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """收入统计。"""
    with Session(engine) as db:
        query = select(Bill).where(Bill.status == "paid")
        if start_date:
            sd = date.fromisoformat(start_date)
            query = query.where(Bill.created_at >= datetime(sd.year, sd.month, sd.day))
        if end_date:
            ed = date.fromisoformat(end_date)
            query = query.where(
                Bill.created_at < datetime(ed.year, ed.month, ed.day) + timedelta(days=1)
            )

        bills = db.exec(query).all()

        total_electricity = sum(b.electricity_fee for b in bills)
        total_service = sum(b.service_fee for b in bills)
        total_revenue = sum(b.total_fee for b in bills)

        return {
            "totalRevenue": round(total_revenue, 2),
            "electricityRevenue": round(total_electricity, 2),
            "serviceRevenue": round(total_service, 2),
            "paidSessions": len(bills),
        }


def get_utilization_report() -> dict:
    """充电桩利用率统计。"""
    with Session(engine) as db:
        stations = db.exec(select(Station).order_by(Station.id)).all()
        result = []
        for s in stations:
            queue_util = (s.queue_count / s.queue_capacity * 100) if s.queue_capacity else 0
            waiting_util = (s.waiting_count / s.waiting_capacity * 100) if s.waiting_capacity else 0
            charging_util = (s.charging_count / s.charging_capacity * 100) if s.charging_capacity else 0
            result.append({
                "stationId": s.id,
                "stationName": s.name,
                "status": s.status,
                "queueUtilization": round(queue_util, 1),
                "waitingUtilization": round(waiting_util, 1),
                "chargingUtilization": round(charging_util, 1),
                "queueCount": s.queue_count,
                "queueCapacity": s.queue_capacity,
                "waitingCount": s.waiting_count,
                "waitingCapacity": s.waiting_capacity,
                "chargingCount": s.charging_count,
                "chargingCapacity": s.charging_capacity,
            })
        return {"stations": result}


# ═══════════════════════════════════════════
# 辅助
# ═══════════════════════════════════════════

def _bjt_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return (dt + BJT_OFFSET).isoformat()


# ═══════════════════════════════════════════
# 调度日志
# ═══════════════════════════════════════════

def list_schedule_logs(
    page: int = 1,
    page_size: int = 20,
    session_id: int | None = None,
) -> dict:
    """查看调度日志（分页）。"""
    with Session(engine) as db:
        query = select(ScheduleLog)
        if session_id:
            query = query.where(ScheduleLog.session_id == session_id)

        total = db.exec(select(func.count()).select_from(query.subquery())).one()
        query = query.order_by(ScheduleLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        rows = db.exec(query).all()

        result = []
        for log in rows:
            session = db.get(ChargingSession, log.session_id)
            from_st = db.get(Station, log.from_station_id) if log.from_station_id else None
            to_st = db.get(Station, log.to_station_id) if log.to_station_id else None
            result.append({
                "id": log.id,
                "sessionId": log.session_id,
                "licensePlate": db.get(User, session.user_id).license_plate if session and db.get(User, session.user_id) else "未知",
                "fromStation": from_st.name if from_st else None,
                "toStation": to_st.name if to_st else None,
                "fromZone": log.from_zone,
                "toZone": log.to_zone,
                "triggeredBy": log.triggered_by,
                "detail": log.detail,
                "createdAt": _bjt_iso(log.created_at),
            })

        return {"list": result, "page": page, "pageSize": page_size, "total": total}
