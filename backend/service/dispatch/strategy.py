"""
调度策略 — 重新调度排队/等待/充电中的车辆到其他充电桩。

ShortestTimeSingleStrategy：
  逐个计算会话的最佳目标充电桩，选择预估等待时间最短的桩。
  充电中的会话也会被停止并作为排队会话重新调度。
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station
from model.user_protocol import UserProtocol

logger = logging.getLogger("charge-system.strategy")


class RedistributeResult:
    """重新调度结果"""
    def __init__(self):
        self.moved_sessions: list[dict] = []
        self.failed_sessions: list[dict] = []


class ShortestTimeSingleStrategy:
    """
    对每个会话，在所有 running 且有空余排队容量的充电桩中，
    选择预估等待时间最短的桩。

    支持排队/等待/充电三种状态的会话：
    - 排队 / 等待：直接移动到目标桩排队区
    - 充电中：立即停止充电，重置为排队状态，移动到目标桩排队区
    """

    def redistribute(
        self,
        session_ids: list[int],
        exclude_station_id: int,
        exclude_station_ids: list[int] | None = None,
    ) -> RedistributeResult:
        result = RedistributeResult()
        if not session_ids:
            return result

        with Session(engine) as db:
            candidates = self._get_candidates(db, exclude_station_id, exclude_station_ids)
            if not candidates:
                for sid in session_ids:
                    result.failed_sessions.append({
                        "sessionId": sid,
                        "reason": "没有可用的目标充电桩",
                    })
                return result

            for sid in session_ids:
                session = db.get(ChargingSession, sid)
                if session is None:
                    continue

                # 如果正在充电 → 立即停止
                if session.status == "charging":
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
                    logger.info(f"紧急停止: 会话 {sid} 已停止充电，准备重调度")

                best = self._find_best_candidate(db, session, candidates)
                if best is None:
                    result.failed_sessions.append({
                        "sessionId": sid,
                        "reason": "所有目标桩队列已满或无兼容协议",
                    })
                    continue

                old_station_id = session.station_id
                old_station = db.get(Station, old_station_id)

                # 从原桩移除
                if old_station:
                    if session.zone == "queue":
                        old_station.queue_count = max(0, old_station.queue_count - 1)
                    elif session.zone == "waiting":
                        old_station.waiting_count = max(0, old_station.waiting_count - 1)

                # 排入目标桩排队区
                new_pos = best.queue_count + 1
                best.queue_count += 1
                session.station_id = best.id
                session.queue_position = new_pos
                session.status = "queued"
                session.zone = "queue"
                session.advance_ready = False

                db.add(session)
                db.add(best)
                if old_station:
                    db.add(old_station)

                db.add(ScheduleLog(
                    session_id=session.id,
                    from_station_id=old_station_id,
                    to_station_id=best.id,
                    from_zone="queue" if session.zone == "queue" else "waiting",
                    to_zone="queue",
                    triggered_by="system",
                    detail=f"紧急停止重调度: {(old_station.name if old_station else '')} → {best.name}",
                ))

                result.moved_sessions.append({
                    "sessionId": session.id,
                    "fromStationId": old_station_id,
                    "toStationId": best.id,
                    "toStationName": best.name,
                    "newPosition": new_pos,
                })

            db.commit()

        return result

    def _get_candidates(
        self,
        db: Session,
        exclude_station_id: int,
        exclude_station_ids: list[int] | None,
    ) -> list[Station]:
        exclude_ids = {exclude_station_id}
        if exclude_station_ids:
            exclude_ids.update(exclude_station_ids)
        return db.exec(
            select(Station).where(
                Station.status == "running",
                Station.id.notin_(exclude_ids),
            )
        ).all()

    def _find_best_candidate(
        self,
        db: Session,
        session: ChargingSession,
        candidates: list[Station],
    ) -> Station | None:
        """找最佳目标充电桩（排入排队区）。"""
        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == session.user_id)
        ).all()
        user_pids = {up.protocol_id for up in up_rows}

        from model.station import StationProtocol
        best = None
        best_score = float("inf")

        for station in candidates:
            if station.queue_count >= station.queue_capacity:
                continue

            sp_rows = db.exec(
                select(StationProtocol).where(StationProtocol.station_id == station.id)
            ).all()
            station_pids = {sp.protocol_id for sp in sp_rows}
            if not user_pids.intersection(station_pids):
                continue

            # 评分 = 排队等待分钟数（排队+等待人数 × 平均充电时长/充电位）
            avg_min = 30
            waiting_minutes = (station.queue_count + station.waiting_count) * avg_min // max(station.charging_capacity, 1)
            if waiting_minutes < best_score:
                best_score = waiting_minutes
                best = station

        return best
