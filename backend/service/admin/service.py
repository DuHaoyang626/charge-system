"""
管理端服务 — 配置管理、会话管理、账单管理、报表统计。
"""
import logging
from datetime import datetime, timedelta, date

from sqlmodel import Session, select, func

from core.database import engine
from core.exceptions import AppException
from core.logger import system_logger
from model.bill import Bill
from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
from model.session import ChargingSession
from model.station import Station
from model.user import User
from model.schedule_log import ScheduleLog
from service.session.service import build_session_detail

logger = logging.getLogger("charge-system.admin")

BJT_OFFSET = timedelta(hours=8)


# ═══════════════════════════════════════════
# 配置管理
# ═══════════════════════════════════════════

def _to_minutes(t: str) -> int:
    """将 HH:mm 转为当天分钟数。"""
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _validate_prices_no_conflict(prices: list[dict]) -> None:
    """校验电价时段无时间重叠。"""
    # 将每个时段展开为 (start_min, end_min) 区间
    intervals: list[tuple[int, int, str]] = []
    for p in prices:
        start = _to_minutes(p.get("start", ""))
        end = _to_minutes(p.get("end", ""))
        name = p.get("periodName", "")
        if end <= start:
            # 跨天时段，拆为两段检查
            intervals.append((start, 1440, name))
            intervals.append((0, end, name))
        else:
            intervals.append((start, end, name))

    intervals.sort(key=lambda x: x[0])
    for i in range(len(intervals)):
        for j in range(i + 1, len(intervals)):
            if intervals[j][0] < intervals[i][1]:
                raise ValueError(
                    f"电价时段 \"{intervals[i][2]}\" 与 \"{intervals[j][2]}\" 存在时间冲突"
                )


def get_all_configs() -> dict:
    """获取全部配置（严格遵循 API 接口说明）。"""
    with Session(engine) as db:
        configs = db.exec(select(GlobalConfig)).all()
        config_map = {c.config_key: c.config_value for c in configs}

        prices = db.exec(
            select(ElectricityPrice).order_by(ElectricityPrice.start_time)
        ).all()
        tiers = db.exec(
            select(ServiceFeeTier).order_by(ServiceFeeTier.min_minutes)
        ).all()

        return {
            "schedulingAlgorithm": config_map.get("scheduling_algorithm", "shortest_time_single"),
            "baseServiceFee": float(config_map.get("base_service_fee", 5.0)),
            "electricityPrices": [
                {
                    "periodName": p.period_name,
                    "start": p.start_time,
                    "end": p.end_time,
                    "pricePerKwh": p.price_per_kwh,
                }
                for p in prices
            ],
            "serviceFeeTiers": [
                {
                    "minMinutes": t.min_minutes,
                    "maxMinutes": t.max_minutes,
                    "ratePerMinute": t.rate_per_minute,
                }
                for t in tiers
            ],
        }


def update_configs(data: dict) -> dict:
    """统一更新配置（严格遵循 API 接口说明）。"""
    with Session(engine) as db:
        now = datetime.utcnow()

        # ── 顶层标量配置 ──
        scalar_map = {
            "schedulingAlgorithm": "scheduling_algorithm",
            "baseServiceFee": "base_service_fee",
        }
        for api_key, db_key in scalar_map.items():
            if api_key in data:
                existing = db.exec(
                    select(GlobalConfig).where(GlobalConfig.config_key == db_key)
                ).first()
                if existing:
                    existing.config_value = str(data[api_key])
                    existing.updated_at = now
                    db.add(existing)

        # ── 电价时段：校验冲突后全量替换 ──
        if "electricityPrices" in data:
            prices_in = data["electricityPrices"]
            if not prices_in:
                raise ValueError("电价时段列表不能为空")

            # 校验时间冲突
            _validate_prices_no_conflict(prices_in)

            # 校验各时段字段完整性
            for item in prices_in:
                if not item.get("periodName"):
                    raise ValueError("电价时段名称不能为空")
                if not item.get("start") or not item.get("end"):
                    raise ValueError("电价时段起止时间不能为空")
                if item.get("pricePerKwh") is None or item["pricePerKwh"] < 0:
                    raise ValueError("电价必须 >= 0")

            # 删除旧电价
            old = db.exec(select(ElectricityPrice)).all()
            for o in old:
                db.delete(o)
            db.flush()

            # 插入新电价
            for item in prices_in:
                db.add(ElectricityPrice(
                    period_name=item["periodName"],
                    start_time=item["start"],
                    end_time=item["end"],
                    price_per_kwh=item["pricePerKwh"],
                ))

        # ── 服务费阶梯：全量替换 ──
        if "serviceFeeTiers" in data:
            tiers_in = data["serviceFeeTiers"]
            if not tiers_in:
                raise ValueError("服务费阶梯列表不能为空")

            for item in tiers_in:
                if item.get("minMinutes") is None or item["minMinutes"] < 0:
                    raise ValueError("服务费阶梯最小分钟数不能 < 0")
                if item.get("ratePerMinute") is None or item["ratePerMinute"] < 0:
                    raise ValueError("服务费阶梯费率不能 < 0")
                if item.get("maxMinutes") is not None and item["maxMinutes"] <= item.get("minMinutes", 0):
                    raise ValueError("服务费阶梯最大分钟数必须大于最小分钟数")

            old_tiers = db.exec(select(ServiceFeeTier)).all()
            for t in old_tiers:
                db.delete(t)
            db.flush()

            for item in tiers_in:
                db.add(ServiceFeeTier(
                    tier_name=item.get("tierName"),
                    min_minutes=item["minMinutes"],
                    max_minutes=item.get("maxMinutes"),
                    rate_per_minute=item["ratePerMinute"],
                ))

        db.commit()

    system_logger.info("admin", f"管理员更新配置: {list(data.keys())}")
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
    """查看所有用户会话（分页）— 严格遵循 API 接口说明。"""
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

            # 计算进度
            progress = 0
            if s.status == "charging" and s.requested_energy_kwh > 0:
                progress = min(100, int(s.charged_energy_kwh / s.requested_energy_kwh * 100))
            elif s.status == "completed":
                progress = 100

            result.append({
                "sessionId": s.id,
                "user": {
                    "id": s.user_id,
                    "licensePlate": user.license_plate if user else "未知",
                },
                "station": {
                    "id": s.station_id,
                    "name": station.name if station else "未知",
                },
                "status": s.status,
                "requestedEnergyKwh": s.requested_energy_kwh,
                "chargedEnergyKwh": s.charged_energy_kwh,
                "progress": progress,
                "createdAt": _bjt_iso(s.created_at),
            })

        return {"list": result, "page": page, "pageSize": page_size, "total": total}


def get_admin_session_detail(session_id: int) -> dict | None:
    """查看任意会话详情 — 严格遵循 API 接口说明（同 GET /sessions/:id + user 字段）。"""
    with Session(engine) as db:
        s = db.get(ChargingSession, session_id)
        if s is None:
            return None
        user = db.get(User, s.user_id)

        # 复用共享的会话详情构建（同 GET /sessions/:id 的完整结构）
        detail = build_session_detail(s)

        # 添加用户摘要
        detail["user"] = {
            "id": s.user_id,
            "licensePlate": user.license_plate if user else "未知",
        }
        return detail


# ═══════════════════════════════════════════
# 账单管理
# ═══════════════════════════════════════════

def list_all_bills(
    page: int = 1,
    page_size: int = 20,
    user_id: int | None = None,
    license_plate: str | None = None,
    station_id: int | None = None,
    payment_status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """查看所有账单（分页）— 严格遵循 API 接口说明。"""
    with Session(engine) as db:
        query = select(Bill)
        if user_id:
            query = query.where(Bill.user_id == user_id)
        if license_plate:
            query = query.join(User).where(User.license_plate == license_plate)
        if station_id:
            query = query.where(Bill.station_id == station_id)
        if payment_status:
            query = query.where(Bill.status == payment_status)
        if start_date:
            sd = date.fromisoformat(start_date)
            query = query.where(Bill.created_at >= datetime(sd.year, sd.month, sd.day))
        if end_date:
            ed = date.fromisoformat(end_date)
            query = query.where(
                Bill.created_at < datetime(ed.year, ed.month, ed.day) + timedelta(days=1)
            )

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
                "user": {
                    "id": b.user_id,
                    "licensePlate": user.license_plate if user else "未知",
                },
                "station": {
                    "id": b.station_id,
                    "name": b.station_name,
                },
                "chargedEnergyKwh": b.total_energy_kwh,
                "totalFee": b.total_fee,
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

def _period_key(dt: datetime, granularity: str) -> str:
    """根据粒度生成周期标识。"""
    if granularity == "day":
        return dt.strftime("%Y-%m-%d")
    elif granularity == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    else:  # month
        return dt.strftime("%Y-%m")


def _load_bills_in_range(
    start_date: str | None, end_date: str | None, status: str = "paid"
) -> list:
    """按日期范围加载账单（在当前会话内完成）。"""
    with Session(engine) as db:
        query = select(Bill).where(Bill.status == status)
        if start_date:
            sd = date.fromisoformat(start_date)
            query = query.where(Bill.created_at >= datetime(sd.year, sd.month, sd.day))
        if end_date:
            ed = date.fromisoformat(end_date)
            query = query.where(
                Bill.created_at < datetime(ed.year, ed.month, ed.day) + timedelta(days=1)
            )
        rows = db.exec(query).all()
        # 提取需要的数据到普通字典，避免 detached session 问题
        result = []
        for r in rows:
            result.append({
                "energy": r.total_energy_kwh,
                "fee": r.total_fee,
                "elec_fee": r.electricity_fee,
                "svc_fee": r.service_fee,
                "created": r.created_at,
            })
        return result


def get_charging_volume_report(
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "month",
) -> dict:
    """充电量统计 — 严格遵循 API 接口说明。"""
    bills = _load_bills_in_range(start_date, end_date)
    total_energy = sum(b["energy"] for b in bills)

    from collections import defaultdict
    buckets: dict[str, dict] = defaultdict(lambda: {"energyKwh": 0.0, "sessions": 0})
    for b in bills:
        pk = _period_key(b["created"], granularity)
        buckets[pk]["energyKwh"] += b["energy"]
        buckets[pk]["sessions"] += 1

    data_points = []
    for period in sorted(buckets.keys()):
        bkt = buckets[period]
        data_points.append({
            "period": period,
            "energyKwh": round(bkt["energyKwh"], 2),
            "sessions": bkt["sessions"],
        })

    return {
        "totalEnergyKwh": round(total_energy, 2),
        "totalSessions": len(bills),
        "dataPoints": data_points,
    }


def get_revenue_report(
    start_date: str | None = None,
    end_date: str | None = None,
    granularity: str = "month",
) -> dict:
    """收入统计 — 严格遵循 API 接口说明。"""
    bills = _load_bills_in_range(start_date, end_date)
    total_revenue = sum(b["fee"] for b in bills)
    total_electricity = sum(b["elec_fee"] for b in bills)
    total_service = sum(b["svc_fee"] for b in bills)

    from collections import defaultdict
    buckets: dict[str, dict] = defaultdict(lambda: {"revenue": 0.0, "electricity": 0.0, "service": 0.0})
    for b in bills:
        pk = _period_key(b["created"], granularity)
        buckets[pk]["revenue"] += b["fee"]
        buckets[pk]["electricity"] += b["elec_fee"]
        buckets[pk]["service"] += b["svc_fee"]

    data_points = []
    for period in sorted(buckets.keys()):
        bkt = buckets[period]
        data_points.append({
            "period": period,
            "revenue": round(bkt["revenue"], 2),
            "electricity": round(bkt["electricity"], 2),
            "service": round(bkt["service"], 2),
        })

    return {
        "totalRevenue": round(total_revenue, 2),
        "electricityRevenue": round(total_electricity, 2),
        "serviceRevenue": round(total_service, 2),
        "dataPoints": data_points,
    }


def get_utilization_report(
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """充电桩利用率统计 — 严格遵循 API 接口说明。"""
    with Session(engine) as db:
        stations = db.exec(select(Station).order_by(Station.id)).all()

    # 计算时间区间内的小时数
    from datetime import datetime as dt_mod
    now = dt_mod.utcnow()
    if end_date:
        ed = date.fromisoformat(end_date)
        period_end = datetime(ed.year, ed.month, ed.day, 23, 59, 59)
    else:
        period_end = now
    if start_date:
        sd = date.fromisoformat(start_date)
        period_start = datetime(sd.year, sd.month, sd.day)
    else:
        # 默认查最近 30 天
        period_start = period_end - timedelta(days=30)

    total_hours_in_period = max(1, (period_end - period_start).total_seconds() / 3600)

    # 获取该时间段内各桩的充电会话
    with Session(engine) as db:
        session_query = select(ChargingSession).where(
            ChargingSession.status == "completed",
            ChargingSession.completed_at >= period_start,
            ChargingSession.completed_at <= period_end,
        )
        completed_sessions = db.exec(session_query).all()

    station_charging_hours: dict[int, float] = {}
    for s in completed_sessions:
        sid = s.station_id
        if s.started_charging_at and s.completed_at:
            secs = (s.completed_at - s.started_charging_at).total_seconds()
            station_charging_hours[sid] = station_charging_hours.get(sid, 0) + secs / 3600

    result = []
    total_charging_hours_all = 0.0
    total_available_hours_all = 0.0

    for s in stations:
        ch = round(station_charging_hours.get(s.id, 0), 2)
        ah = round(s.charging_capacity * total_hours_in_period, 2)
        util = round(min(1.0, ch / ah if ah > 0 else 0), 4)

        total_charging_hours_all += ch
        total_available_hours_all += ah

        result.append({
            "stationId": s.id,
            "stationName": s.name,
            "utilization": util,
            "totalChargingHours": ch,
            "totalAvailableHours": ah,
        })

    overall = round(min(1.0, total_charging_hours_all / total_available_hours_all
                        if total_available_hours_all > 0 else 0), 4)

    return {
        "overallUtilization": overall,
        "stations": result,
    }


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
