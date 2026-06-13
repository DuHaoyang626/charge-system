"""
队列服务 — 入队、换队、取消。

三个区域流转：
    排队区 (queue)  →  等待区 (waiting)  →  充电区 (charging)
"""

import logging
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from core.exceptions import AppException, Err
from model.session import ChargingSession
from model.station import Station

logger = logging.getLogger("charge-system.queue")


def enqueue(db: Session, session: ChargingSession, station: Station) -> int:
    """
    将会话加入指定充电桩的排队区队尾。
    与调用方共享同一个 db Session（事务一致性）。

    返回 queue_position。
    """
    db_station = db.get(Station, station.id)
    if db_station is None:
        raise AppException(*Err.STATION_NOT_FOUND)
    if db_station.status != "running":
        raise AppException(*Err.STATION_NOT_RUNNING)
    if db_station.queue_count >= db_station.queue_capacity:
        raise AppException(*Err.QUEUE_FULL)

    position = db_station.queue_count + 1
    session.station_id = db_station.id
    session.status = "queued"
    session.zone = "queue"
    session.queue_position = position
    db.add(session)

    db_station.queue_count += 1
    db.add(db_station)

    return position


def move_to_station(session_id: int, target_station_id: int, user_id: int) -> dict:
    """
    将会话从当前桩排队区移到目标桩排队区队尾。
    """
    with Session(engine) as db:
        db_session = db.get(ChargingSession, session_id)
        if db_session is None:
            raise AppException(*Err.NOT_FOUND)
        if db_session.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)
        if db_session.status != "queued":
            raise AppException(400, "等待区中不可换队")

        target = db.get(Station, target_station_id)
        if target is None:
            raise AppException(*Err.STATION_NOT_FOUND)
        if target.status != "running":
            raise AppException(400, "目标充电桩已停止运行，无法换队")
        if target.queue_count >= target.queue_capacity:
            raise AppException(*Err.TARGET_STATION_FULL)
        if target.id == db_session.station_id:
            raise AppException(400, "目标充电桩与当前桩相同")

        # 从原桩移除
        old_station = db.get(Station, db_session.station_id)
        if old_station:
            old_station.queue_count = max(0, old_station.queue_count - 1)
            db.add(old_station)

        # 加入目标桩
        new_position = target.queue_count + 1
        target.queue_count += 1
        db.add(target)

        # 更新会话
        db_session.station_id = target.id
        db_session.queue_position = new_position
        db.add(db_session)
        db.commit()

        return {
            "sessionId": db_session.id,
            "stationId": target.id,
            "zone": "queue",
            "queuePosition": new_position,
            "estimatedWaitMinutes": _estimate_wait(target),
        }


def cancel_session(session_id: int, user_id: int) -> dict:
    """
    取消充电会话。
    """
    with Session(engine) as db:
        db_session = db.get(ChargingSession, session_id)
        if db_session is None:
            raise AppException(*Err.NOT_FOUND)
        if db_session.user_id != user_id:
            raise AppException(*Err.FORBIDDEN)
        if db_session.status == "charging":
            raise AppException(*Err.CANNOT_CANCEL_CHARGING)
        if db_session.status in ("completed", "cancelled"):
            raise AppException(*Err.SESSION_COMPLETED)

        station = db.get(Station, db_session.station_id)

        # 从桩计数中移除
        if station:
            if db_session.zone == "queue":
                station.queue_count = max(0, station.queue_count - 1)
            elif db_session.zone == "waiting":
                station.waiting_count = max(0, station.waiting_count - 1)
            db.add(station)

        # 更新会话
        db_session.status = "cancelled"
        db_session.zone = None
        db_session.cancelled_at = datetime.utcnow()
        db_session.queue_position = None

        bill_data = None
        message = "已取消，无费用"

        # waiting 态取消，收基础服务费
        if db_session.zone == "waiting" or db_session.entered_waiting_at is not None:
            base_fee = station.base_service_fee if station else 5.0
            from model.bill import Bill

            bill = Bill(
                session_id=db_session.id,
                user_id=db_session.user_id,
                station_id=db_session.station_id,
                station_name=station.name if station else "",
                total_fee=base_fee,
                electricity_fee=0,
                service_fee=base_fee,
                total_service_fee=base_fee,
                status="unpaid",
            )
            db.add(bill)
            db.flush()
            bill_data = {
                "billId": bill.id,
                "baseServiceFee": base_fee,
                "totalFee": base_fee,
                "paymentStatus": "unpaid",
            }
            message = f"已取消，需支付基础服务费 ¥{base_fee:.2f}"

        db.add(db_session)
        db.commit()

        return {
            "sessionId": db_session.id,
            "status": "cancelled",
            "message": message,
            "bill": bill_data,
        }


def _estimate_wait(station: Station) -> int:
    total = station.queue_count + station.waiting_count
    if total == 0:
        return 0
    avg_charging_minutes = 30
    return total * avg_charging_minutes // (station.charging_capacity or 1)
