"""
自动调度循环 — 后台常驻协程

生命周期：
    1. FastAPI lifespan 启动 dispatch_loop.start()
    2. 每 10 秒执行一次 tick
    3. 每个 tick 分三步：推进充电 → 排队→等待 → 等待→充电
    4. FastAPI 关闭时 dispatch_loop.stop()
"""

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from core.database import engine
from model.protocol import Protocol
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station

if TYPE_CHECKING:
    pass

logger = logging.getLogger("dispatch_loop")

# 常量
DISPATCH_INTERVAL = 10  # 调度间隔（秒）


class DispatchLoop:
    """自动调度循环 — 后台常驻协程"""

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self):
        """启动调度循环。"""
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("自动调度循环已启动 (间隔 10s)")

    async def stop(self):
        """停止调度循环。"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("自动调度循环已停止")

    async def _loop(self):
        """调度主循环。"""
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                logger.error(f"调度 tick 异常: {e}", exc_info=True)
            await asyncio.sleep(DISPATCH_INTERVAL)

    async def _tick(self):
        """单次调度 tick — 按顺序执行三个步骤。"""
        await self._tick_charging()
        await self._dispatch_queue_to_waiting()
        await self._dispatch_waiting_to_charging()

    # ──────────────────────────────────────────────
    # 步骤 1：推进充电进度
    # ──────────────────────────────────────────────

    async def _tick_charging(self):
        """扫描所有 charging 会话，推进电量，检测完成。"""
        with Session(engine) as db:
            sessions = db.exec(
                select(ChargingSession).where(ChargingSession.status == "charging")
            ).all()
            now = datetime.utcnow()

            for s in sessions:
                if not s.started_charging_at or not s.protocol_id:
                    continue

                # 获取协议功率
                protocol = db.get(Protocol, s.protocol_id)
                if not protocol:
                    continue

                # 计算已充电量
                elapsed_h = (now - s.started_charging_at).total_seconds() / 3600
                energy = round(protocol.power_kw * elapsed_h, 2)

                if energy >= s.requested_energy_kwh:
                    # 充满 → 自动完成
                    energy = s.requested_energy_kwh
                    s.status = "completed"
                    s.zone = None
                    s.completed_at = now
                    s.charged_energy_kwh = energy
                    db.add(s)

                    # 减少充电桩计数
                    station = db.get(Station, s.station_id)
                    if station:
                        station.charging_count = max(0, station.charging_count - 1)
                        db.add(station)

                    # 生成账单
                    from model.bill import Bill

                    station_name = station.name if station else ""
                    bill = Bill(
                        session_id=s.id,
                        user_id=s.user_id,
                        station_id=s.station_id,
                        station_name=station_name,
                        total_energy_kwh=energy,
                        electricity_fee=0,
                        service_fee=0,
                        total_service_fee=0,
                        total_fee=0,
                        status="unpaid",
                    )
                    db.add(bill)
                    logger.info(
                        f"会话 {s.id} 充电完成，已生成账单"
                    )

                    # 检查该桩是否可以 stopping → stopped
                    if station and station.status == "stopping":
                        if (station.queue_count == 0
                                and station.waiting_count == 0
                                and station.charging_count == 0):
                            station.status = "stopped"
                            db.add(station)
                            logger.info(f"充电桩 {station.name} 队列已清空，自动停止")
                else:
                    # 更新已充电量
                    s.charged_energy_kwh = energy
                    db.add(s)

            db.commit()

    # ──────────────────────────────────────────────
    # 步骤 2：排队区 → 等待区
    # ──────────────────────────────────────────────

    async def _dispatch_queue_to_waiting(self):
        """每个桩：等待区有空位则将排队区队首移入。"""
        with Session(engine) as db:
            stations = db.exec(
                select(Station).where(Station.status.in_(["running", "stopping"]))
            ).all()

            for station in stations:
                moved = False
                while (
                    station.waiting_count < station.waiting_capacity
                    and station.queue_count > 0
                ):
                    # 取排队区队首
                    session = db.exec(
                        select(ChargingSession)
                        .where(
                            ChargingSession.station_id == station.id,
                            ChargingSession.zone == "queue",
                            ChargingSession.status == "queued",
                        )
                        .order_by(ChargingSession.queue_position)
                        .limit(1)
                    ).first()

                    if not session:
                        break

                    new_position = station.waiting_count + 1

                    # 更新会话
                    session.status = "waiting"
                    session.zone = "waiting"
                    session.entered_waiting_at = datetime.utcnow()
                    session.queue_position = new_position
                    db.add(session)

                    # 更新桩计数
                    station.queue_count = max(0, station.queue_count - 1)
                    station.waiting_count += 1
                    db.add(station)

                    # 记录调度日志
                    db.add(ScheduleLog(
                        session_id=session.id,
                        from_station_id=station.id,
                        to_station_id=station.id,
                        from_zone="queue",
                        to_zone="waiting",
                        triggered_by="system",
                    ))

                    moved = True

                if moved:
                    db.flush()

            db.commit()

    # ──────────────────────────────────────────────
    # 步骤 3：等待区 → 充电区
    # ──────────────────────────────────────────────

    async def _dispatch_waiting_to_charging(self):
        """每个桩：充电区有空位则将等待区队首移入。"""
        with Session(engine) as db:
            stations = db.exec(
                select(Station).where(Station.status == "running")
            ).all()

            for station in stations:
                moved = False
                while (
                    station.charging_count < station.charging_capacity
                    and station.waiting_count > 0
                ):
                    # 取等待区队首
                    session = db.exec(
                        select(ChargingSession)
                        .where(
                            ChargingSession.station_id == station.id,
                            ChargingSession.zone == "waiting",
                            ChargingSession.status == "waiting",
                        )
                        .order_by(ChargingSession.queue_position)
                        .limit(1)
                    ).first()

                    if not session:
                        break

                    # 自动匹配最佳协议
                    protocol = self._best_match(db, session, station)
                    if not protocol:
                        # 无兼容协议，跳过此辆（保留在等待区）
                        logger.warning(
                            f"会话 {session.id} 无兼容协议，跳过"
                        )
                        # 将其移到最后，避免阻塞
                        session.queue_position = station.waiting_count + 1
                        db.add(session)
                        break

                    # 移入充电区
                    session.status = "charging"
                    session.zone = "charging"
                    session.protocol_id = protocol.id
                    session.started_charging_at = datetime.utcnow()
                    session.queue_position = None
                    db.add(session)

                    # 更新桩计数
                    station.waiting_count = max(0, station.waiting_count - 1)
                    station.charging_count += 1
                    db.add(station)

                    # 记录调度日志
                    db.add(ScheduleLog(
                        session_id=session.id,
                        from_station_id=station.id,
                        to_station_id=station.id,
                        from_zone="waiting",
                        to_zone="charging",
                        triggered_by="system",
                        detail=f"协议: {protocol.name} ({protocol.power_kw}kW)",
                    ))

                    moved = True

                if moved:
                    db.flush()

            db.commit()

    # ──────────────────────────────────────────────
    # 辅助方法：最佳协议匹配
    # ──────────────────────────────────────────────

    def _best_match(self, db: Session, session: ChargingSession, station: Station) -> Protocol | None:
        """
        选择兼容的最高功率协议。

        取用户的充电协议列表 ∩ 充电桩支持协议列表，选功率最高的。
        """
        from model.user_protocol import UserProtocol

        # 用户支持的协议
        up_rows = db.exec(
            select(UserProtocol).where(UserProtocol.user_id == session.user_id)
        ).all()
        user_protocol_ids = {up.protocol_id for up in up_rows}

        # 充电桩支持的协议
        sp_rows = db.exec(
            select(Station.station_protocols)  # This won't work, use StationProtocol
        ).all() if False else []

        # 正确方式：查询 StationProtocol
        from model.station import StationProtocol

        sp_rows = db.exec(
            select(StationProtocol).where(StationProtocol.station_id == station.id)
        ).all()
        station_protocol_ids = {sp.protocol_id for sp in sp_rows}

        # 取交集
        compatible_ids = user_protocol_ids & station_protocol_ids
        if not compatible_ids:
            return None

        # 取功率最高的协议
        protocols = db.exec(
            select(Protocol)
            .where(Protocol.id.in_(compatible_ids))
            .order_by(Protocol.power_kw.desc())
        ).all()

        return protocols[0] if protocols else None
