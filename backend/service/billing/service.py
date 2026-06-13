"""
账单服务 — 生成、查询、支付。
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlmodel import Session, select, func

from core.database import engine
from core.exceptions import AppException, Err
from model.bill import Bill
from model.config import ElectricityPrice, ServiceFeeTier
from model.session import ChargingSession
from model.station import Station
from model.protocol import Protocol
from model.user import User
from service.billing.engine import (
    PriceSlot, ServiceTier,
    calculate_electricity_fee, calculate_service_fee,
)

logger = logging.getLogger("charge-system.billing")
BJT_OFFSET = timedelta(hours=8)


def _get_price_slots(db: Session) -> list[PriceSlot]:
    """从数据库加载电价时段配置。"""
    rows = db.exec(
        select(ElectricityPrice).order_by(ElectricityPrice.start_time)
    ).all()
    return [
        PriceSlot(
            period_name=r.period_name,
            start_time=r.start_time,
            end_time=r.end_time,
            price_per_kwh=r.price_per_kwh,
        )
        for r in rows
    ]


def _get_service_tiers(db: Session) -> list[ServiceTier]:
    """从数据库加载服务费阶梯配置。"""
    rows = db.exec(
        select(ServiceFeeTier).order_by(ServiceFeeTier.min_minutes)
    ).all()
    return [
        ServiceTier(
            tier_name=r.tier_name or f"{r.min_minutes}-{r.max_minutes or '∞'}分钟",
            min_minutes=r.min_minutes,
            max_minutes=r.max_minutes,
            rate_per_minute=r.rate_per_minute,
        )
        for r in rows
    ]


def _build_electricity_details(
    session: ChargingSession,
    prices: list[PriceSlot],
) -> list[dict[str, Any]]:
    """构建电费时段明细（用于响应）。"""
    if not session.started_charging_at or not session.completed_at:
        return []
    result = calculate_electricity_fee(
        start_time=session.started_charging_at,
        end_time=session.completed_at,
        total_energy_kwh=session.charged_energy_kwh,
        prices=prices,
    )
    return [
        {
            "period": item.name,
            "energy": item.quantity,
            "price": item.unit_price,
            "fee": item.fee,
        }
        for item in result.items
    ]


def _build_service_fee_tiers(
    charging_minutes: int,
    base_fee: float,
    tiers: list[ServiceTier],
) -> list[dict[str, Any]]:
    """构建服务费阶梯明细（用于响应）。"""
    result = calculate_service_fee(
        charging_minutes=charging_minutes,
        base_fee=base_fee,
        tiers=tiers,
    )
    return [
        {
            "tier": item.name,
            "minutes": item.quantity if item.name != "基础服务费" else 0,
            "rate": item.unit_price,
            "fee": item.fee,
        }
        for item in result.items
    ]


def generate_bill(session_id: int) -> Bill | None:
    """
    为指定 session 生成账单。
    如果账单已存在则直接返回。
    """
    with Session(engine) as db:
        existing = db.exec(
            select(Bill).where(Bill.session_id == session_id)
        ).first()
        if existing:
            return existing

        session = db.get(ChargingSession, session_id)
        if session is None:
            return None

        station = db.get(Station, session.station_id)
        protocol = db.get(Protocol, session.protocol_id) if session.protocol_id else None

        energy = session.charged_energy_kwh or 0

        # 充电时长（分钟）
        charging_minutes = 0
        if session.started_charging_at and session.completed_at:
            seconds = (session.completed_at - session.started_charging_at).total_seconds()
            charging_minutes = max(1, int(seconds / 60))

        # 计费
        prices = _get_price_slots(db)
        tiers = _get_service_tiers(db)
        base_fee = station.base_service_fee if station else 5.0

        elec_result = calculate_electricity_fee(
            start_time=session.started_charging_at or datetime.utcnow(),
            end_time=session.completed_at or datetime.utcnow(),
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
        total_fee = round(electricity_fee + total_service_fee, 2)

        bill = Bill(
            session_id=session.id,
            user_id=session.user_id,
            station_id=session.station_id,
            station_name=station.name if station else "",
            protocol_name=protocol.name if protocol else "",
            power_kw=protocol.power_kw if protocol else 0,
            total_energy_kwh=energy,
            electricity_fee=electricity_fee,
            base_service_fee=base_fee,
            time_service_fee=time_service_fee,
            service_fee=total_service_fee,
            total_fee=total_fee,
            charging_minutes=charging_minutes,
            status="unpaid",
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        logger.info(
            f"账单 {bill.id} 已生成: session={session_id}, "
            f"电费={electricity_fee}, 服务费={total_service_fee}, 合计={total_fee}"
        )
        return bill


def get_bill(bill_id: int, user_id: int | None = None) -> dict[str, Any] | None:
    """
    获取账单详情。
    如果 user_id 不为 None，校验账单属于该用户。
    """
    with Session(engine) as db:
        bill = db.get(Bill, bill_id)
        if bill is None:
            return None

        if user_id is not None and bill.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)

        session = db.get(ChargingSession, bill.session_id)
        station = db.get(Station, bill.station_id) if bill.station_id else None
        user = db.get(User, bill.user_id) if bill.user_id else None

        # 构建明细
        prices = _get_price_slots(db)
        tiers = _get_service_tiers(db)
        base_fee = station.base_service_fee if station else 5.0

        # 用电费明细
        electricity_details = []
        if session and session.started_charging_at and session.completed_at:
            electricity_details = _build_electricity_details(session, prices)

        # 服务费明细
        service_fee_tiers = _build_service_fee_tiers(
            bill.charging_minutes, base_fee, tiers,
        )

        charging_duration = None
        if session and session.started_charging_at and session.completed_at:
            seconds = (session.completed_at - session.started_charging_at).total_seconds()
            h, remainder = divmod(int(seconds), 3600)
            m, s = divmod(remainder, 60)
            charging_duration = f"{h:02d}:{m:02d}:{s:02d}"

        def bjt_iso(dt: datetime | None) -> str | None:
            if dt is None:
                return None
            return (dt + BJT_OFFSET).isoformat()

        result: dict[str, Any] = {
            "id": bill.id,
            "sessionId": bill.session_id,
            "user": {
                "id": user.id,
                "licensePlate": user.license_plate,
            } if user else None,
            "station": {
                "id": bill.station_id,
                "name": bill.station_name,
            },
            "chargingDuration": charging_duration,
            "chargingMinutes": bill.charging_minutes,
            "chargedEnergyKwh": bill.total_energy_kwh,
            "electricityFee": bill.electricity_fee,
            "electricityDetails": electricity_details,
            "baseServiceFee": bill.base_service_fee,
            "serviceFeeTiers": service_fee_tiers,
            "timeServiceFee": bill.time_service_fee,
            "totalServiceFee": bill.service_fee,
            "totalFee": bill.total_fee,
            "paymentStatus": bill.status,
            "createdAt": bjt_iso(bill.created_at),
            "paidAt": bjt_iso(bill.paid_at),
        }
        if bill.transaction_id:
            result["transactionId"] = bill.transaction_id

        return result


def get_user_bills(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    payment_status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """
    获取用户的历史账单列表（分页）。
    """
    with Session(engine) as db:
        query = select(Bill).where(Bill.user_id == user_id)

        if payment_status:
            query = query.where(Bill.status == payment_status)
        if start_date:
            from datetime import date
            sd = date.fromisoformat(start_date)
            from datetime import datetime
            query = query.where(Bill.created_at >= datetime(sd.year, sd.month, sd.day))
        if end_date:
            from datetime import date
            ed = date.fromisoformat(end_date)
            from datetime import datetime, timedelta
            query = query.where(
                Bill.created_at < datetime(ed.year, ed.month, ed.day) + timedelta(days=1)
            )

        # 总数
        total = db.exec(select(func.count()).select_from(query.subquery())).one()

        # 分页
        query = query.order_by(Bill.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        bills = db.exec(query).all()

        def bjt_iso(dt: datetime | None) -> str | None:
            if dt is None:
                return None
            return (dt + BJT_OFFSET).isoformat()

        bill_list = []
        for b in bills:
            station = db.get(Station, b.station_id) if b.station_id else None
            session = db.get(ChargingSession, b.session_id) if b.session_id else None

            charging_duration = None
            if session and session.started_charging_at and session.completed_at:
                seconds = (session.completed_at - session.started_charging_at).total_seconds()
                h, remainder = divmod(int(seconds), 3600)
                m, s = divmod(remainder, 60)
                charging_duration = f"{h:02d}:{m:02d}:{s:02d}"

            bill_list.append({
                "billId": b.id,
                "sessionId": b.session_id,
                "station": {
                    "id": b.station_id,
                    "name": b.station_name,
                },
                "chargingDuration": charging_duration,
                "chargedEnergyKwh": b.total_energy_kwh,
                "totalFee": b.total_fee,
                "paymentStatus": b.status,
                "createdAt": bjt_iso(b.created_at),
                "paidAt": bjt_iso(b.paid_at),
            })

        return {
            "list": bill_list,
            "page": page,
            "pageSize": page_size,
            "total": total,
        }


def process_payment(bill_id: int, user_id: int, payment_method: str) -> dict[str, Any]:
    """
    模拟支付。
    校验账单存在、属于当前用户、且未支付。
    """
    with Session(engine) as db:
        bill = db.get(Bill, bill_id)
        if bill is None:
            raise AppException(*Err.BILL_NOT_FOUND)
        if bill.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)
        if bill.status == "paid":
            raise AppException(*Err.BILL_ALREADY_PAID)

        now = datetime.utcnow()
        bill.status = "paid"
        bill.paid_at = now
        bill.transaction_id = f"TXN{now.strftime('%Y%m%d%H%M%S')}{bill_id:04d}"
        db.add(bill)
        db.commit()
        db.refresh(bill)

        paid_at_iso = (bill.paid_at + BJT_OFFSET).isoformat()

        logger.info(
            f"账单 {bill_id} 支付成功: method={payment_method}, "
            f"transaction={bill.transaction_id}"
        )

        return {
            "billId": bill.id,
            "paymentStatus": bill.status,
            "totalFee": bill.total_fee,
            "paidAt": paid_at_iso,
            "transactionId": bill.transaction_id,
        }
