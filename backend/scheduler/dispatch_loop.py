"""
自动调度循环 — 后台常驻协程

生命周期：
    1. FastAPI lifespan 启动 dispatch_loop.start()
    2. 每 10 秒执行一次 tick
    3. 每个 tick 分三步：推进充电 → 排队→等待 → 等待→充电
    4. FastAPI 关闭时 dispatch_loop.stop()

充电推进使用增量累加：每次 tick 计算自上次以来的增量能量，
即使中途切换协议也不会丢失已有进度。
"""

import asyncio
import logging
from datetime import datetime

from sqlmodel import Session, select

from core.database import engine
from model.protocol import Protocol
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station

logger = logging.getLogger("dispatch_loop")

DISPATCH_INTERVAL = 10


class DispatchLoop:
    """自动调度循环 — 后台常驻协程"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False
        # 记录每个 charging 会话的上次 tick 时间（用于增量电量计算）
        self._last_tick: dict[int, datetime] = {}

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("自动调度循环已启动 (间隔 10s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("自动调度循环已停止")

    async def _loop(self):
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"调度 tick 异常: {e}", exc_info=True)
            await asyncio.sleep(DISPATCH_INTERVAL)

    async def _tick(self):
        await self._tick_charging()
        await self._dispatch_queue_to_waiting()
        await self._dispatch_waiting_to_charging()

    # ──────────────────────────────────────────────
    # 步骤 1：推进充电进度（增量累加）
    # ──────────────────────────────────────────────

    async def _tick_charging(self):
        """扫描所有 charging 会话，增量推进电量。

        每次 tick 只计算自上次 tick 以来的增量和，不重新从 0 算。
        这样即使中途切换协议（功率变化），已有进度也不会丢失。
        """
        now = datetime.utcnow()
        sessions_added = set()

        with Session(engine, expire_on_commit=False) as db:
            sessions = db.exec(
                select(ChargingSession).where(ChargingSession.status == "charging")
            ).all()

            for s in sessions:
                if not s.started_charging_at or not s.protocol_id:
                    continue

                protocol = db.get(Protocol, s.protocol_id)
                if not protocol:
                    continue

                # 增量时间：自上次 tick 或开始时间以来的秒数
                last_check = self._last_tick.get(s.id)
                if last_check is None:
                    # 首次：从 started_charging_at 算到 now
                    delta_h = (now - s.started_charging_at).total_seconds() / 3600
                    base = 0.0
                else:
                    delta_h = (now - last_check).total_seconds() / 3600
                    base = s.charged_energy_kwh or 0.0

                # 增量能量
                increment = round(protocol.power_kw * delta_h, 2)
                energy = round(base + increment, 2)

                if energy >= s.requested_energy_kwh:
                    energy = s.requested_energy_kwh
                    s.status = "completed"
                    s.zone = None
                    s.completed_at = now
                    s.charged_energy_kwh = energy
                    db.add(s)

                    station = db.get(Station, s.station_id)
                    if station:
                        station.charging_count = max(0, station.charging_count - 1)
                        db.add(station)

                    from model.bill import Bill
                    station_name = station.name if station else ""
                    protocol_obj = db.get(Protocol, s.protocol_id)
                    protocol_name = protocol_obj.name if protocol_obj else ""
                    electricity_fee = round(energy * 0.8, 2)
                    base_fee = station.base_service_fee if station else 5.0
                    bill = Bill(
                        session_id=s.id, user_id=s.user_id,
                        station_id=s.station_id, station_name=station_name,
                        protocol_name=protocol_name,
                        total_energy_kwh=energy,
                        electricity_fee=electricity_fee,
                        service_fee=base_fee,
                        total_service_fee=base_fee,
                        total_fee=round(electricity_fee + base_fee, 2),
                        status="unpaid",
                    )
                    db.add(bill)
                    logger.info(f"会话 {s.id} 充电完成，已生成账单")

                    if station and station.status == "stopping":
                        if (station.queue_count == 0
                                and station.waiting_count == 0
                                and station.charging_count == 0):
                            station.status = "stopped"
                            db.add(station)
                            logger.info(f"充电桩 {station.name} 队列已清空，自动停止")

                    # 完成后移除跟踪
                    self._last_tick.pop(s.id, None)
                else:
                    s.charged_energy_kwh = energy
                    db.add(s)
                    sessions_added.add(s.id)
                    self._last_tick[s.id] = now

            db.commit()

        # 清理不在 charging 状态的残留记录
        active_ids = {s.id for s in sessions}
        for sid in list(self._last_tick.keys()):
            if sid not in active_ids:
                self._last_tick.pop(sid, None)

    # ──────────────────────────────────────────────
    # 步骤 2：排队区 → 等待区
    # ──────────────────────────────────────────────

    async def _dispatch_queue_to_waiting(self):
        with Session(engine, expire_on_commit=False) as db:
            stations = db.exec(
                select(Station).where(Station.status.in_(["running", "stopping"]))
            ).all()

            for station in stations:
                if station.queue_count == 0:
                    continue

                # 取排队区队首一个未标记的会话
                session = db.exec(
                    select(ChargingSession)
                    .where(
                        ChargingSession.station_id == station.id,
                        ChargingSession.zone == "queue",
                        ChargingSession.status == "queued",
                        ChargingSession.advance_ready == False,
                    )
                    .order_by(ChargingSession.queue_position)
                    .limit(1)
                ).first()

                if not session:
                    continue

                has_charging_slot = station.charging_count < station.charging_capacity
                waiting_was_empty = station.waiting_count == 0
                both_free = has_charging_slot and waiting_was_empty

                if both_free and station.waiting_count < station.waiting_capacity:
                    # ── 两区都空 → 自动推进 queue→waiting → 标记充电确认 ──
                    new_position = station.waiting_count + 1
                    session.status = "waiting"
                    session.zone = "waiting"
                    session.entered_waiting_at = datetime.utcnow()
                    session.queue_position = new_position
                    db.add(session)

                    station.queue_count = max(0, station.queue_count - 1)
                    station.waiting_count += 1
                    db.add(station)

                    db.add(ScheduleLog(
                        session_id=session.id,
                        from_station_id=station.id, to_station_id=station.id,
                        from_zone="queue", to_zone="waiting",
                        triggered_by="system",
                    ))

                    # 检查该会话是否有兼容协议，有则直接标记充电确认
                    if self._best_match(db, session, station):
                        session.advance_ready = True
                        logger.info(
                            f"会话 {session.id} 两区空闲→自动进入等待区，标记充电确认"
                        )
                    db.commit()

                elif station.waiting_count < station.waiting_capacity:
                    # ── 仅等待区有空 → 标记排队确认 ──
                    session.advance_ready = True
                    db.add(session)
                    db.commit()
                    logger.info(f"会话 {session.id} 标记为就绪（排队→等待）")
                    # 每次 tick 只处理一个，避免连续弹出多个等待确认
                    break

            db.commit()

    # ──────────────────────────────────────────────
    # 步骤 3：等待区 → 充电区
    # ──────────────────────────────────────────────

    async def _dispatch_waiting_to_charging(self):
        with Session(engine, expire_on_commit=False) as db:
            stations = db.exec(
                select(Station).where(Station.status == "running")
            ).all()

            for station in stations:
                if station.charging_count >= station.charging_capacity:
                    continue
                if station.waiting_count == 0:
                    continue

                # 取等待区队首一个未标记的会话
                session = db.exec(
                    select(ChargingSession)
                    .where(
                        ChargingSession.station_id == station.id,
                        ChargingSession.zone == "waiting",
                        ChargingSession.status == "waiting",
                        ChargingSession.advance_ready == False,
                    )
                    .order_by(ChargingSession.queue_position)
                    .limit(1)
                ).first()

                if not session:
                    continue

                protocol = self._best_match(db, session, station)
                if not protocol:
                    # 无兼容协议 → 重新排位
                    session.queue_position = station.waiting_count + 1
                    db.add(session)
                    db.flush()
                    continue

                # 标记为就绪，等待用户确认
                session.advance_ready = True
                db.add(session)
                logger.info(
                    f"会话 {session.id} 标记为就绪（等待→充电），"
                    f"推荐协议: {protocol.name} ({protocol.power_kw}kW)"
                )
                # 每次 tick 只处理一个
                break

            db.commit()

    # ──────────────────────────────────────────────
    # 辅助方法
    # ──────────────────────────────────────────────

    def _best_match(self, db: Session, session: ChargingSession, station: Station) -> Protocol | None:
        from model.user_protocol import UserProtocol
        from model.station import StationProtocol

        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == session.user_id)
        ).all()
        user_ids = {up.protocol_id for up in up_rows}

        sp_rows = db.exec(
            select(StationProtocol).where(StationProtocol.station_id == station.id)
        ).all()
        station_ids = {sp.protocol_id for sp in sp_rows}

        compatible = user_ids & station_ids
        if not compatible:
            return None

        protocols = db.exec(
            select(Protocol)
            .where(Protocol.id.in_(compatible))
            .order_by(Protocol.power_kw.desc())
        ).all()
        return protocols[0] if protocols else None
