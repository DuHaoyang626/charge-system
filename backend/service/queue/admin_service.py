"""
管理端队列服务 — 查看、重排、移动。
"""
import logging
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from core.exceptions import AppException
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station
from model.user import User

logger = logging.getLogger("charge-system.admin_queue")


def list_all_queues() -> dict:
    """获取所有充电桩的三个区域车辆列表。"""
    with Session(engine) as db:
        stations = db.exec(select(Station).order_by(Station.id)).all()
        result = []
        for s in stations:
            queue_sessions = _get_zone_sessions(db, s.id, "queue", "queued")
            waiting_sessions = _get_zone_sessions(db, s.id, "waiting", "waiting")
            charging_sessions = _get_charging_sessions(db, s.id)

            result.append({
                "stationId": s.id,
                "stationName": s.name,
                "status": s.status,
                "capacity": {
                    "queue": {"current": s.queue_count, "max": s.queue_capacity},
                    "waiting": {"current": s.waiting_count, "max": s.waiting_capacity},
                    "charging": {"current": s.charging_count, "max": s.charging_capacity},
                },
                "queueList": queue_sessions,
                "waitingList": waiting_sessions,
                "chargingList": charging_sessions,
            })
        return {"stations": result}


def reorder_queue(
    station_id: int,
    zone: str,
    session_id: int,
    new_position: int,
) -> dict:
    """
    重新排列指定区域中的队列位置。

    将 session_id 移到 new_position，其余会话自动顺移。
    zone: "queue" | "waiting"
    """
    if zone not in ("queue", "waiting"):
        raise AppException(400, "zone 必须是 queue 或 waiting")

    status_map = {"queue": "queued", "waiting": "waiting"}

    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(404, "充电桩不存在")

        # 获取该区域所有会话（按当前位置排序）
        sessions = db.exec(
            select(ChargingSession)
            .where(
                ChargingSession.station_id == station_id,
                ChargingSession.zone == zone,
                ChargingSession.status == status_map[zone],
            )
            .order_by(ChargingSession.queue_position)
        ).all()

        if not sessions:
            raise AppException(400, "该区域无车辆")

        # 校验 session_id 在列表中
        current_ids = [s.id for s in sessions]
        if session_id not in current_ids:
            raise AppException(404, "会话不在该区域中")

        if new_position < 1 or new_position > len(sessions):
            raise AppException(400, f"位置必须在 1 ~ {len(sessions)} 之间")

        # 重新排序
        current_positions = {s.id: s.queue_position or 0 for s in sessions}
        target_idx = new_position - 1
        current_idx = current_ids.index(session_id)

        # 重新分配所有位置
        ordered = list(sessions)
        ordered.insert(target_idx, ordered.pop(current_idx))

        for i, s in enumerate(ordered):
            new_pos = i + 1
            s.queue_position = new_pos
            db.add(s)

        db.add(ScheduleLog(
            session_id=session_id,
            from_station_id=station_id,
            to_station_id=station_id,
            from_zone=zone,
            to_zone=zone,
            triggered_by="admin",
            detail=f"重排: 位置 {current_positions[session_id]} → {new_position}",
        ))
        db.commit()

        return {
            "stationId": station_id,
            "zone": zone,
            "sessionId": session_id,
            "oldPosition": current_positions[session_id],
            "newPosition": new_position,
        }


def move_session_to_station(
    session_id: int,
    target_station_id: int,
    target_position: int | None = None,
) -> dict:
    """
    将会话从一个桩移动到另一个桩的对应区域。

    保留会话当前的 zone（queue → queue, waiting → waiting）。
    仅当两个桩都 running 时可用。
    """
    with Session(engine) as db:
        session = db.get(ChargingSession, session_id)
        if session is None:
            raise AppException(404, "会话不存在")
        if session.status not in ("queued", "waiting"):
            raise AppException(400, "仅排队或等待状态的会话可以移动")

        source_station = db.get(Station, session.station_id)
        target_station = db.get(Station, target_station_id)
        if target_station is None:
            raise AppException(404, "目标充电桩不存在")
        if target_station.status != "running":
            raise AppException(400, "目标充电桩未运行")

        zone = session.zone or "queue"
        old_station_id = session.station_id
        old_position = session.queue_position

        # 容量检查
        if zone == "queue":
            if target_station.queue_count >= target_station.queue_capacity:
                raise AppException(400, "目标充电桩排队区已满")
            target_station.queue_count += 1
            if source_station:
                source_station.queue_count = max(0, source_station.queue_count - 1)
        else:  # waiting
            if target_station.waiting_count >= target_station.waiting_capacity:
                raise AppException(400, "目标充电桩等待区已满")
            target_station.waiting_count += 1
            if source_station:
                source_station.waiting_count = max(0, source_station.waiting_count - 1)

        # 更新会话
        session.station_id = target_station_id
        if target_position:
            session.queue_position = target_position
        else:
            # 放到队尾
            session.queue_position = (
                target_station.queue_count if zone == "queue"
                else target_station.waiting_count
            )

        # 原桩剩余会话重新排位
        remaining = db.exec(
            select(ChargingSession)
            .where(
                ChargingSession.station_id == old_station_id,
                ChargingSession.zone == zone,
                ChargingSession.status == session.status,
                ChargingSession.id != session_id,
            )
            .order_by(ChargingSession.queue_position)
        ).all()
        for i, s in enumerate(remaining):
            s.queue_position = i + 1
            db.add(s)

        db.add(session)
        if source_station:
            db.add(source_station)
        db.add(target_station)

        db.add(ScheduleLog(
            session_id=session.id,
            from_station_id=old_station_id,
            to_station_id=target_station_id,
            from_zone=zone,
            to_zone=zone,
            triggered_by="admin",
            detail=f"管理员移桩: {source_station.name if source_station else ''} → {target_station.name}",
        ))
        db.commit()

        return {
            "sessionId": session.id,
            "fromStationId": old_station_id,
            "toStationId": target_station_id,
            "zone": zone,
            "newPosition": session.queue_position,
        }


# ── 内部辅助 ──


def _get_zone_sessions(db: Session, station_id: int, zone: str, status: str) -> list[dict]:
    """获取指定区域的会话列表。"""
    sessions = db.exec(
        select(ChargingSession)
        .where(
            ChargingSession.station_id == station_id,
            ChargingSession.status == status,
            ChargingSession.zone == zone,
        )
        .order_by(ChargingSession.queue_position)
    ).all()

    result = []
    for s in sessions:
        user = db.get(User, s.user_id)
        result.append({
            "sessionId": s.id,
            "licensePlate": user.license_plate if user else "未知",
            "position": s.queue_position or 0,
            "requestedEnergyKwh": s.requested_energy_kwh,
            "status": s.status,
            "advanceReady": s.advance_ready,
        })
    return result


def _get_charging_sessions(db: Session, station_id: int) -> list[dict]:
    """获取充电区的会话列表。"""
    sessions = db.exec(
        select(ChargingSession)
        .where(
            ChargingSession.station_id == station_id,
            ChargingSession.status == "charging",
        )
        .order_by(ChargingSession.queue_position)
    ).all()

    result = []
    for s in sessions:
        user = db.get(User, s.user_id)
        from model.protocol import Protocol
        protocol = db.get(Protocol, s.protocol_id) if s.protocol_id else None

        now = datetime.utcnow()
        progress = 0
        if s.requested_energy_kwh > 0:
            progress = min(100, int(s.charged_energy_kwh / s.requested_energy_kwh * 100))

        result.append({
            "sessionId": s.id,
            "licensePlate": user.license_plate if user else "未知",
            "chargedEnergyKwh": s.charged_energy_kwh,
            "targetEnergyKwh": s.requested_energy_kwh,
            "progress": progress,
            "protocol": {
                "id": protocol.id,
                "name": protocol.name,
                "powerKw": protocol.power_kw,
            } if protocol else None,
        })
    return result
