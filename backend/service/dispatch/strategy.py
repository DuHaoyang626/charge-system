"""
调度策略 — 五种批量调度算法，策略模式。

算法标识（存入 global_configs.scheduling_algorithm）：
  - shortest_time_single  : 单次调度最短时长
  - batch_shortest        : 批量调度最短总时长（匈牙利算法）
  - priority              : 优先级调度
  - time_order            : 时间顺序调度
  - fault_recovery        : 充电中故障恢复
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from core.logger import system_logger
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station
from model.user_protocol import UserProtocol

logger = logging.getLogger("charge-system.strategy")

AVG_CHARGE_MINUTES = 30


class RedistributeResult:
    """重新调度结果"""
    def __init__(self):
        self.moved_sessions: list[dict] = []
        self.failed_sessions: list[dict] = []


# ═══════════════════════════════════════════════
# 抽象策略接口
# ═══════════════════════════════════════════════

class DispatchStrategy(ABC):
    """调度策略接口 — 重新调度会话到目标桩排队区"""

    @abstractmethod
    def redistribute(
        self,
        session_ids: list[int],
        exclude_station_id: int,
        exclude_station_ids: list[int] | None = None,
    ) -> RedistributeResult:
        ...


# ═══════════════════════════════════════════════
# 辅助方法
# ═══════════════════════════════════════════════

def _get_candidates(db: Session, exclude_station_id: int,
                    exclude_station_ids: list[int] | None) -> list[Station]:
    exclude = {exclude_station_id}
    if exclude_station_ids:
        exclude.update(exclude_station_ids)
    return db.exec(
        select(Station).where(Station.status == "running", Station.id.notin_(exclude))
    ).all()


def _get_user_protocol_ids(db: Session, user_id: int) -> set[int]:
    return {r.protocol_id for r in
            db.exec(select(UserProtocol).where(UserProtocol.user_id == user_id)).all()}


def _get_station_protocol_ids(db: Session, station_id: int) -> set[int]:
    from model.station import StationProtocol
    return {r.protocol_id for r in
            db.exec(select(StationProtocol).where(StationProtocol.station_id == station_id)).all()}


def _estimate_wait(station: Station, queue_pos: int = 0) -> int:
    """预估从排队到开始充电的等待分钟数。"""
    total_ahead = station.queue_count + station.waiting_count + queue_pos
    slots = max(station.charging_capacity, 1)
    return (total_ahead + 1) * AVG_CHARGE_MINUTES // slots


def _is_compatible(db: Session, user_id: int, station: Station) -> bool:
    """检查用户与充电桩是否有兼容协议。"""
    user_pids = _get_user_protocol_ids(db, user_id)
    station_pids = _get_station_protocol_ids(db, station.id)
    return bool(user_pids & station_pids)


def _do_move(db: Session, session: ChargingSession,
             target: Station) -> dict:
    """执行移动：从原桩移除 → 排入目标桩排队区。"""
    old_station_id = session.station_id
    old_station = db.get(Station, old_station_id)

    if old_station:
        if session.zone == "queue" or session.status == "queued":
            old_station.queue_count = max(0, old_station.queue_count - 1)
        elif session.zone == "waiting" or session.status == "waiting":
            old_station.waiting_count = max(0, old_station.waiting_count - 1)

    new_pos = target.queue_count + 1
    target.queue_count += 1
    session.station_id = target.id
    session.queue_position = new_pos
    session.status = "queued"
    session.zone = "queue"
    session.advance_ready = False

    db.add(session)
    db.add(target)
    if old_station:
        db.add(old_station)

    db.add(ScheduleLog(
        session_id=session.id,
        from_station_id=old_station_id,
        to_station_id=target.id,
        from_zone="queue",
        to_zone="queue",
        triggered_by="system",
        detail=f"重调度: {(old_station.name if old_station else '')} → {target.name}",
    ))

    return {
        "sessionId": session.id,
        "fromStationId": old_station_id,
        "toStationId": target.id,
        "toStationName": target.name,
        "newPosition": new_pos,
    }


def _stop_charging(db: Session, session: ChargingSession):
    """立即停止充电会话，重置为排队状态。"""
    station = db.get(Station, session.station_id)
    if station:
        station.charging_count = max(0, station.charging_count - 1)
        db.add(station)
    session.status = "queued"
    session.zone = "queue"
    session.protocol_id = None
    session.started_charging_at = None
    session.charged_energy_kwh = 0
    session.advance_ready = False
    logger.info(f"紧急停止: 会话 {session.id} 已停止充电")


def _best_available_station(db: Session, session: ChargingSession,
                            candidates: list[Station]) -> Station | None:
    """找最佳目标充电桩（有空余排队容量 + 兼容协议）。"""
    best = None
    best_score = float("inf")
    for s in candidates:
        if s.queue_count >= s.queue_capacity:
            continue
        if not _is_compatible(db, session.user_id, s):
            continue
        score = _estimate_wait(s)
        if score < best_score:
            best_score = score
            best = s
    return best


# ═══════════════════════════════════════════════
# 算法 1：单次调度最短时长
# ═══════════════════════════════════════════════

class ShortestTimeSingleStrategy(DispatchStrategy):
    """对每个会话遍历兼容桩计算 Tⱼ，选最短的。"""

    def redistribute(self, session_ids: list[int], exclude_station_id: int,
                     exclude_station_ids: list[int] | None = None) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result
        with Session(engine) as db:
            candidates = _get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({"sessionId": sid, "reason": "无可用目标桩"})
                return result
            for sid in session_ids:
                s = db.get(ChargingSession, sid)
                if not s:
                    continue
                if s.status == "charging":
                    _stop_charging(db, s)
                best = _best_available_station(db, s, candidates)
                if not best:
                    result.failed_sessions.append({"sessionId": sid, "reason": "队列满或无兼容协议"})
                    continue
                result.moved_sessions.append(_do_move(db, s, best))
            db.commit()
        return result


# ═══════════════════════════════════════════════
# 算法 2：批量调度最短总时长（匈牙利算法）
# ═══════════════════════════════════════════════

def _hungarian(cost: list[list[float]]) -> list[int]:
    """
    匈牙利算法求最小指派。
    cost[i][j] = 车辆 i 分配到桩 j 的成本。
    返回 assignment[i] = j（桩索引），若无法分配返回 -1。
    """
    n = len(cost)          # 车辆数
    m = len(cost[0]) if cost else 0  # 桩数
    if n == 0 or m == 0:
        return []

    # 扩展为方阵
    size = max(n, m)
    matrix = [[0.0] * size for _ in range(size)]
    for i in range(n):
        for j in range(m):
            matrix[i][j] = cost[i][j]
    # 填充行/列用大数
    BIG = 1e9
    for i in range(n):
        for j in range(m, size):
            matrix[i][j] = BIG
    for i in range(n, size):
        for j in range(size):
            matrix[i][j] = BIG

    # 标准匈牙利算法实现
    u = [0.0] * (size + 1)
    v = [0.0] * (size + 1)
    p = [0] * (size + 1)
    way = [0] * (size + 1)

    for i in range(1, size + 1):
        p[0] = i
        j0 = 0
        minv = [BIG] * (size + 1)
        used = [False] * (size + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = BIG
            j1 = 0
            for j in range(1, size + 1):
                if not used[j]:
                    cur = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(size + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    # 提取结果
    assignment = [-1] * n
    for j in range(1, size + 1):
        if p[j] > 0 and p[j] <= n and j <= m:
            assignment[p[j] - 1] = j - 1
    return assignment


class BatchShortestStrategy(DispatchStrategy):
    """构建 N×M 成本矩阵，匈牙利算法求全局最优。"""

    def redistribute(self, session_ids: list[int], exclude_station_id: int,
                     exclude_station_ids: list[int] | None = None) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result
        with Session(engine) as db:
            candidates = _get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({"sessionId": sid, "reason": "无可用目标桩"})
                return result

            sessions = []
            for sid in session_ids:
                s = db.get(ChargingSession, sid)
                if s:
                    if s.status == "charging":
                        _stop_charging(db, s)
                    sessions.append(s)

            n = len(sessions)
            m = len(candidates)

            # 构建成本矩阵
            cost = []
            for s in sessions:
                row = []
                for st in candidates:
                    if st.queue_count >= st.queue_capacity:
                        row.append(1e9)
                    elif not _is_compatible(db, s.user_id, st):
                        row.append(1e9)
                    else:
                        row.append(float(_estimate_wait(st)))
                cost.append(row)

            # 匈牙利算法分配
            assignment = _hungarian(cost)
            used_stations = set()

            for i, s in enumerate(sessions):
                j = assignment[i]
                if j < 0 or j >= m:
                    result.failed_sessions.append({"sessionId": s.id, "reason": "无可用分配"})
                    continue
                st = candidates[j]
                if st.queue_count >= st.queue_capacity:
                    result.failed_sessions.append({"sessionId": s.id, "reason": "目标桩队列已满"})
                    continue
                result.moved_sessions.append(_do_move(db, s, st))

            db.commit()
        return result


# ═══════════════════════════════════════════════
# 算法 3：优先级调度
# ═══════════════════════════════════════════════

class PriorityStrategy(DispatchStrategy):
    """按用户优先级排序，高优先先分配。"""

    def redistribute(self, session_ids: list[int], exclude_station_id: int,
                     exclude_station_ids: list[int] | None = None) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result
        with Session(engine) as db:
            candidates = _get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({"sessionId": sid, "reason": "无可用目标桩"})
                return result

            # 收集会话 + 用户优先级
            items = []
            for sid in session_ids:
                s = db.get(ChargingSession, sid)
                if not s:
                    continue
                if s.status == "charging":
                    _stop_charging(db, s)
                from model.user import User
                user = db.get(User, s.user_id)
                priority = user.priority if user else 0
                items.append((priority, s))

            # 按优先级降序 (VIP=1 优先)
            items.sort(key=lambda x: -x[0])

            for _, s in items:
                best = _best_available_station(db, s, candidates)
                if not best:
                    result.failed_sessions.append({"sessionId": s.id, "reason": "队列满或无兼容协议"})
                    continue
                result.moved_sessions.append(_do_move(db, s, best))

            db.commit()
        return result


# ═══════════════════════════════════════════════
# 算法 4：时间顺序调度
# ═══════════════════════════════════════════════

class TimeOrderStrategy(DispatchStrategy):
    """按请求时间排序车辆，依次分配可用充电桩。"""

    def redistribute(self, session_ids: list[int], exclude_station_id: int,
                     exclude_station_ids: list[int] | None = None) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result
        with Session(engine) as db:
            candidates = _get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({"sessionId": sid, "reason": "无可用目标桩"})
                return result

            items = []
            for sid in session_ids:
                s = db.get(ChargingSession, sid)
                if not s:
                    continue
                if s.status == "charging":
                    _stop_charging(db, s)
                items.append((s.created_at, s))

            items.sort(key=lambda x: x[0])  # 最早请求优先

            for _, s in items:
                best = _best_available_station(db, s, candidates)
                if not best:
                    result.failed_sessions.append({"sessionId": s.id, "reason": "队列满或无兼容协议"})
                    continue
                result.moved_sessions.append(_do_move(db, s, best))

            db.commit()
        return result


# ═══════════════════════════════════════════════
# 算法 5：充电中故障恢复
# ═══════════════════════════════════════════════

class FaultRecoveryStrategy(DispatchStrategy):
    """
    保存已充电量快照，优先恢复充电中车辆到兼容桩。
    充电中车辆优先分配 → 排队/等待车辆再分配。
    """

    def redistribute(self, session_ids: list[int], exclude_station_id: int,
                     exclude_station_ids: list[int] | None = None) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result
        with Session(engine) as db:
            candidates = _get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({"sessionId": sid, "reason": "无可用目标桩"})
                return result

            charging_items = []
            other_items = []

            for sid in session_ids:
                s = db.get(ChargingSession, sid)
                if not s:
                    continue
                if s.status == "charging":
                    # 保存已充电量快照到 charged_energy_kwh（已存）
                    charging_items.append(s)
                    _stop_charging(db, s)
                else:
                    other_items.append(s)

            # 充电中车辆优先分配
            ordered = charging_items + other_items

            for s in ordered:
                best = _best_available_station(db, s, candidates)
                if not best:
                    result.failed_sessions.append({"sessionId": s.id, "reason": "队列满或无兼容协议"})
                    continue
                result.moved_sessions.append(_do_move(db, s, best))

            db.commit()
        return result


# ═══════════════════════════════════════════════
# 策略工厂
# ═══════════════════════════════════════════════

_STRATEGY_MAP: dict[str, type[DispatchStrategy]] = {
    "shortest_time_single": ShortestTimeSingleStrategy,
    "batch_shortest": BatchShortestStrategy,
    "priority": PriorityStrategy,
    "time_order": TimeOrderStrategy,
    "fault_recovery": FaultRecoveryStrategy,
}

ALGORITHM_LABELS: dict[str, str] = {
    "shortest_time_single": "单次调度最短时长",
    "batch_shortest": "批量调度最短总时长（匈牙利算法）",
    "priority": "优先级调度（VIP 优先）",
    "time_order": "时间顺序调度（FIFO）",
    "fault_recovery": "充电中故障恢复优先",
}


def get_strategy(algorithm: str | None = None) -> DispatchStrategy:
    """获取策略实例。algorithm 为 None 时从数据库读取当前配置。"""
    if algorithm is None:
        algorithm = _get_configured_algorithm()
    cls = _STRATEGY_MAP.get(algorithm)
    if cls is None:
        logger.warning(f"未知算法 {algorithm}，使用默认 shortest_time_single")
        system_logger.warning("strategy", f"未知调度算法 {algorithm}，使用默认 shortest_time_single")
        cls = ShortestTimeSingleStrategy
    return cls()


def get_configured_algorithm() -> str:
    """从数据库读取当前调度算法配置。"""
    return _get_configured_algorithm()


def _get_configured_algorithm() -> str:
    """从数据库读取当前调度算法配置。"""
    from model.config import GlobalConfig
    try:
        with Session(engine) as db:
            cfg = db.exec(
                select(GlobalConfig).where(
                    GlobalConfig.config_key == "scheduling_algorithm"
                )
            ).first()
            if cfg and cfg.config_value in _STRATEGY_MAP:
                return cfg.config_value
    except Exception:
        pass
    return "shortest_time_single"
