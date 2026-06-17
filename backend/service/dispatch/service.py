"""
调度服务 — 最优充电桩计算。

find_best_station()：
  从所有 running 且排队区未满的桩中，选择「最早可开始充电」的桩。
  估算公式：预估等待分钟数 = (queue_count + waiting_count) × 平均充电时长 ÷ 充电位数
  平均充电时长从该桩当前充电会话的实际目标电量估算。
"""

import logging

from sqlmodel import Session, select

from core.database import engine
from core.logger import system_logger
from model.session import ChargingSession
from model.station import Station, StationProtocol

logger = logging.getLogger("charge-system.dispatch")

AVG_CHARGE_MINUTES = 30  # 默认平均充电时长（分钟）


def find_best_station(user_id: int, protocol_ids: list[int]) -> Station | None:
    """
    为充电请求选择「最早可开始充电」的充电桩。

    算法：
    1. 筛选 status='running' 且 queue_count < queue_capacity 的桩
    2. 筛选兼容用户所选协议的桩
    3. 对每个候选桩估算等待分钟数
    4. 选等待时间最短的桩

    返回 Station or None。
    """
    with Session(engine) as db:
        stations = db.exec(
            select(Station).where(
                Station.status == "running",
                Station.queue_count < Station.queue_capacity,
            )
        ).all()

        if not stations:
            return None

        # 协议 → 桩映射
        sp_rows = db.exec(
            select(StationProtocol).where(
                StationProtocol.protocol_id.in_(protocol_ids)
            )
        ).all()
        station_pids: dict[int, set[int]] = {}
        for sp in sp_rows:
            station_pids.setdefault(sp.station_id, set()).add(sp.protocol_id)

        protocol_set = set(protocol_ids)

        # 筛选兼容 + 计算等待时间
        best = None
        best_wait = float("inf")

        for s in stations:
            if s.id not in station_pids or not (protocol_set & station_pids[s.id]):
                continue

            wait = _estimate_wait(db, s)
            if wait < best_wait:
                best_wait = wait
                best = s

        if best:
            wait_min = _estimate_wait(db, best)
            logger.info(
                "为用户 %d 选择充电桩 %s (id=%d)，预估等待 %d 分钟",
                user_id, best.name, best.id, wait_min,
            )
            system_logger.info("dispatch", f"用户 {user_id} 调度到充电桩 {best.name}(id={best.id})，预估等待 {wait_min} 分钟")
        else:
            logger.info("为用户 %d 未找到可用充电桩", user_id)
            system_logger.warning("dispatch", f"用户 {user_id} 未找到可用充电桩")

        return best


def _estimate_wait(db: Session, station: Station) -> int:
    """
    估算在该桩从排队到开始充电的等待分钟数。

    考虑：
    - 当前排队和等待人数
    - 平均充电时长（从当前充电中的会话实际目标电量估算）
    - 充电位数
    """
    total_ahead = station.queue_count + station.waiting_count

    # 尝试从当前充电中的会话估算实际平均充电时长
    charging_sessions = db.exec(
        select(ChargingSession).where(
            ChargingSession.station_id == station.id,
            ChargingSession.status == "charging",
        )
    ).all()

    if charging_sessions:
        avg_min = sum(
            max(s.requested_energy_kwh / 60 * 60, 5)
            for s in charging_sessions
        ) / len(charging_sessions)
        # 简化：假设 1kWh ≈ 1 分钟（对 DC 快充偏保守，但安全）
        avg_min = max(avg_min, 10)
    else:
        avg_min = AVG_CHARGE_MINUTES

    slots = max(station.charging_capacity, 1)
    wait = (total_ahead + 1) * avg_min // slots
    return wait
