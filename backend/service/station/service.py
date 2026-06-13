"""
充电桩服务 — 充电桩查询、管理、状态变更的业务逻辑。
"""

import logging
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from core.exceptions import AppException, Err
from model.protocol import Protocol
from model.session import ChargingSession
from model.station import Station, StationProtocol
from model.user import User

logger = logging.getLogger("charge-system.station")


# ──────────────────────────────────────────────
# 用户端：查询
# ──────────────────────────────────────────────


def list_stations() -> dict:
    """获取所有充电桩列表（含协议和预估等待时长）。"""
    with Session(engine) as db:
        stations = db.exec(select(Station).order_by(Station.id)).all()
        result = []
        for s in stations:
            protocols = _get_station_protocols(db, s.id)
            result.append({
                "id": s.id,
                "name": s.name,
                "status": s.status,
                "queueCount": s.queue_count,
                "waitingCount": s.waiting_count,
                "chargingCount": s.charging_count,
                "queueCapacity": s.queue_capacity,
                "waitingCapacity": s.waiting_capacity,
                "chargingCapacity": s.charging_capacity,
                "supportedProtocols": protocols,
                "estimatedWaitMinutes": _estimate_wait(s),
            })
        return {"stations": result}


def get_station_detail(station_id: int) -> dict:
    """获取单个充电桩详情（含三区车辆列表）。"""
    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)

        protocols = _get_station_protocols(db, station_id)

        # 查询三个区域的会话
        queue_sessions = _get_zone_sessions(db, station_id, "queue", "queued")
        waiting_sessions = _get_zone_sessions(db, station_id, "waiting", "waiting")
        charging_sessions = _get_charging_sessions(db, station_id)

        return {
            "id": station.id,
            "name": station.name,
            "status": station.status,
            "queueCapacity": station.queue_capacity,
            "waitingCapacity": station.waiting_capacity,
            "chargingCapacity": station.charging_capacity,
            "queueCount": station.queue_count,
            "waitingCount": station.waiting_count,
            "chargingCount": station.charging_count,
            "queueList": queue_sessions,
            "waitingList": waiting_sessions,
            "chargingList": charging_sessions,
            "supportedProtocols": protocols,
        }


# ──────────────────────────────────────────────
# 管理端：增删改
# ──────────────────────────────────────────────


def create_station(
    name: str,
    queue_capacity: int,
    waiting_capacity: int,
    charging_capacity: int,
    protocol_ids: list[int],
    base_service_fee: float | None = None,
) -> dict:
    """创建充电桩。"""
    with Session(engine) as db:
        # 校验协议
        existing = db.exec(
            select(Protocol).where(Protocol.id.in_(protocol_ids))
        ).all()
        existing_ids = {p.id for p in existing}
        for pid in protocol_ids:
            if pid not in existing_ids:
                raise AppException(400, f"协议 ID {pid} 不存在")

        station = Station(
            name=name,
            queue_capacity=queue_capacity,
            waiting_capacity=waiting_capacity,
            charging_capacity=charging_capacity,
            base_service_fee=base_service_fee or 5.0,
            status="running",
        )
        db.add(station)
        db.flush()

        for pid in protocol_ids:
            db.add(StationProtocol(station_id=station.id, protocol_id=pid))

        db.commit()
        db.refresh(station)

        return {"id": station.id, "name": station.name, "status": station.status}


def update_station(station_id: int, data: dict) -> dict:
    """修改充电桩配置。"""
    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)

        # 逐字段更新
        if "name" in data:
            station.name = data["name"]
        if "queue_capacity" in data:
            val = data["queue_capacity"]
            if val < station.queue_count:
                raise AppException(400, f"排队区容量不能小于当前排队车辆数 {station.queue_count}")
            station.queue_capacity = val
        if "waiting_capacity" in data:
            val = data["waiting_capacity"]
            if val < station.waiting_count:
                raise AppException(400, f"等待区容量不能小于当前等待车辆数 {station.waiting_count}")
            station.waiting_capacity = val
        if "charging_capacity" in data:
            val = data["charging_capacity"]
            if val < station.charging_count:
                raise AppException(400, f"充电区容量不能小于当前充电车辆数 {station.charging_count}")
            station.charging_capacity = val
        if "base_service_fee" in data:
            station.base_service_fee = data["base_service_fee"]
        if "protocol_ids" in data:
            # 重设协议关联
            protocol_ids = data["protocol_ids"]
            existing = db.exec(
                select(Protocol).where(Protocol.id.in_(protocol_ids))
            ).all()
            existing_ids = {p.id for p in existing}
            for pid in protocol_ids:
                if pid not in existing_ids:
                    raise AppException(400, f"协议 ID {pid} 不存在")
            # 删除旧关联
            old_links = db.exec(
                select(StationProtocol).where(StationProtocol.station_id == station_id)
            ).all()
            for link in old_links:
                db.delete(link)
            # 添加新关联
            for pid in protocol_ids:
                db.add(StationProtocol(station_id=station_id, protocol_id=pid))

        station.updated_at = datetime.utcnow()
        db.add(station)
        db.commit()
        db.refresh(station)

        protocols = _get_station_protocols(db, station_id)
        return {
            "id": station.id,
            "name": station.name,
            "status": station.status,
            "supportedProtocols": protocols,
        }


def delete_station(station_id: int) -> None:
    """删除充电桩（三个区域均无车辆时才能删除）。"""
    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)

        if station.queue_count > 0 or station.waiting_count > 0 or station.charging_count > 0:
            raise AppException(
                400,
                f"充电桩仍有车辆，无法删除（排队 {station.queue_count} / 等待 {station.waiting_count} / 充电 {station.charging_count}）",
            )

        # 删除协议关联
        links = db.exec(
            select(StationProtocol).where(StationProtocol.station_id == station_id)
        ).all()
        for link in links:
            db.delete(link)

        db.delete(station)
        db.commit()


def start_station(station_id: int) -> dict:
    """启动充电桩。"""
    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)
        station.status = "running"
        station.updated_at = datetime.utcnow()
        db.add(station)
        db.commit()
        return {"id": station.id, "status": station.status}


def stop_station(station_id: int) -> dict:
    """正常停止充电桩（不再接受新请求，队列处理完毕后自动停止）。"""
    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)
        if station.status == "stopped":
            raise AppException(400, "充电桩已停止")
        station.status = "stopping"
        station.updated_at = datetime.utcnow()
        db.add(station)
        db.commit()
        return {"id": station.id, "status": station.status, "message": "充电桩将在现有队列处理完毕后停止"}


def emergency_stop_station(station_id: int, algorithm: str = "shortest_time_single",
                           exclude_station_ids: list[int] | None = None) -> dict:
    """异常停止充电桩 — 使用配置的算法重新调度所有车辆。"""
    from service.dispatch.strategy import get_strategy

    with Session(engine) as db:
        station = db.get(Station, station_id)
        if station is None:
            raise AppException(*Err.STATION_NOT_FOUND)

        station_name = station.name

        all_session_ids = [
            r.id for r in db.exec(
                select(ChargingSession).where(
                    ChargingSession.station_id == station_id,
                    ChargingSession.status.in_(["queued", "waiting", "charging"]),
                )
            ).all()
        ]

        station.status = "error"
        station.updated_at = datetime.utcnow()
        db.add(station)
        db.commit()

    # 使用策略工厂获取对应算法实例
    strategy = get_strategy(algorithm)
    result = strategy.redistribute(
        session_ids=all_session_ids,
        exclude_station_id=station_id,
        exclude_station_ids=exclude_station_ids,
    )

    total = len(all_session_ids)
    moved_count = len(result.moved_sessions)

    return {
        "message": f"紧急停止完成，{moved_count}/{total} 辆已重调度",
        "status": "error",
        "algorithm": algorithm,
        "redistributedSessions": [
            {
                "sessionId": m["sessionId"],
                "fromStation": station_name,
                "toStation": m["toStationName"],
                "newPosition": m["newPosition"],
            }
            for m in result.moved_sessions
        ],
        "failedSessions": [
            {
                "sessionId": f["sessionId"],
                "fromStation": station_name,
                "reason": f["reason"],
            }
            for f in result.failed_sessions
        ],
    }


# ──────────────────────────────────────────────
# 内部辅助方法
# ──────────────────────────────────────────────


def _get_station_protocols(db: Session, station_id: int) -> list[dict]:
    """获取充电桩支持的协议列表。"""
    rows = db.exec(
        select(StationProtocol, Protocol)
        .join(Protocol, StationProtocol.protocol_id == Protocol.id)
        .where(StationProtocol.station_id == station_id)
    ).all()
    return [
        {"id": p.id, "name": p.name, "powerKw": p.power_kw}
        for _, p in rows
    ]


def _get_zone_sessions(db: Session, station_id: int, zone: str, status: str) -> list[dict]:
    """获取指定区域的会话列表（排队区/等待区）。"""
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
        # 查询用户支持的协议
        from model.user_protocol import UserProtocol
        up_rows = db.exec(
            select(UserProtocol, Protocol)
            .join(Protocol, UserProtocol.protocol_id == Protocol.id)
            .where(UserProtocol.user_id == s.user_id)
        ).all()

        result.append({
            "sessionId": s.id,
            "licensePlate": user.license_plate if user else "未知",
            "position": s.queue_position or 0,
            "requestedEnergyKwh": s.requested_energy_kwh,
            "supportedProtocols": [
                {"id": p.id, "name": p.name, "powerKw": p.power_kw}
                for _, p in up_rows
            ],
            "status": s.status,
            "estimatedWaitMinutes": _estimate_wait_for_session(db, station_id),
        })
    return result


def _get_charging_sessions(db: Session, station_id: int) -> list[dict]:
    """获取充电区的会话列表。"""
    sessions = db.exec(
        select(ChargingSession)
        .where(
            ChargingSession.station_id == station_id,
            ChargingSession.status == "charging",
            ChargingSession.zone == "charging",
        )
        .order_by(ChargingSession.queue_position)
    ).all()

    result = []
    for s in sessions:
        user = db.get(User, s.user_id)
        protocol = db.get(Protocol, s.protocol_id) if s.protocol_id else None
        now = datetime.utcnow()

        # 计算进度
        progress = 0
        if s.requested_energy_kwh > 0:
            progress = min(100, int(s.charged_energy_kwh / s.requested_energy_kwh * 100))

        # 计算预计结束时间
        estimated_end = None
        if s.started_charging_at and s.requested_energy_kwh > 0 and s.charged_energy_kwh < s.requested_energy_kwh:
            elapsed = (now - s.started_charging_at).total_seconds()
            if elapsed > 0 and s.charged_energy_kwh > 0:
                rate = s.charged_energy_kwh / elapsed  # kWh/s
                remaining = (s.requested_energy_kwh - s.charged_energy_kwh) / rate if rate > 0 else 0
                estimated_end = (now.isoformat() if remaining < 3600 * 24 else None)

        result.append({
            "sessionId": s.id,
            "licensePlate": user.license_plate if user else "未知",
            "position": s.queue_position or 0,
            "chargedEnergyKwh": s.charged_energy_kwh,
            "targetEnergyKwh": s.requested_energy_kwh,
            "protocol": {
                "id": protocol.id,
                "name": protocol.name,
                "powerKw": protocol.power_kw,
            } if protocol else None,
            "progress": progress,
            "estimatedEndTime": estimated_end,
        })
    return result


def _estimate_wait(station: Station) -> int:
    """预估等待时长（简化实现）。"""
    total = station.queue_count + station.waiting_count
    if total == 0:
        return 0
    # 假设每辆车平均 30 分钟充电时间
    avg_charging_minutes = 30
    return total * avg_charging_minutes // (station.charging_capacity or 1)


def _estimate_wait_for_session(db: Session, station_id: int) -> int:
    """预估会话等待时长。"""
    station = db.get(Station, station_id)
    if not station:
        return 0
    return _estimate_wait(station)
