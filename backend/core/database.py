"""
数据库连接 — engine + init_db + 种子数据。

在应用 lifecycle 启动时调用 init_db() 自动建表并灌入初始数据。
"""

import logging

from sqlmodel import SQLModel, Session, create_engine, select

from core.config import settings
from core.logger import system_logger

logger = logging.getLogger("charge-system.database")

# ── SQLite 连接配置 ──
# check_same_thread=False 允许 FastAPI 多线程访问同一 SQLite 文件
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


# ──────────────────────────────────────────────
# 初始化
# ──────────────────────────────────────────────


def init_db() -> None:
    """建表 + 灌初始数据（幂等，已有数据则跳过）。"""
    SQLModel.metadata.create_all(engine)
    _migrate_schema()
    _seed_initial_data()
    logger.info("数据库初始化完成")
    system_logger.info("database", "数据库初始化完成（含 log_records 表）")


def _migrate_schema() -> None:
    """在线 schema 迁移（SQLite 不支持 ALTER ADD COLUMN IF NOT EXISTS，用 try/except 兜底）。"""
    from sqlalchemy import text

    migrations = [
        "ALTER TABLE sessions ADD COLUMN advance_ready BOOLEAN NOT NULL DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN base_service_fee FLOAT NOT NULL DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN time_service_fee FLOAT NOT NULL DEFAULT 0",
        "ALTER TABLE bills ADD COLUMN transaction_id VARCHAR(64) DEFAULT NULL",
        "ALTER TABLE bills ADD COLUMN charging_minutes INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE users ADD COLUMN priority INTEGER NOT NULL DEFAULT 0",
    ]
    with Session(engine) as session:
        for sql in migrations:
            try:
                session.execute(text(sql))
                session.commit()
                logger.info(f"Schema 迁移完成: {sql[:60]}...")
            except Exception:
                session.rollback()
                pass

        # 删除 electricity_prices 的 priority 列（如存在）
        try:
            session.execute(text("ALTER TABLE electricity_prices DROP COLUMN priority"))
            session.commit()
            logger.info("Schema 迁移完成: DROP COLUMN priority FROM electricity_prices")
        except Exception:
            session.rollback()
            pass


# ──────────────────────────────────────────────
# 种子数据
# ──────────────────────────────────────────────


def _seed_initial_data() -> None:
    """
    灌初始数据：
    - 3 条充电协议（快充 250kW / 中速 20kW / 基础 7kW）
    - 1 个管理员账号
    - 9 个车辆用户（京A00001‑00009，密码 123456）
    - 5 台充电桩（2 快充 + 3 慢充）
    - 各用户支持全部协议
    - 电价时段 + 服务费阶梯 + 全局配置
    - 2026‑05‑17 ~ 2026‑06‑17 历史充电记录 + 账单（已支付）
    """
    with Session(engine) as session:
        # ── 检查 ──
        existing = session.exec(select(Protocol).limit(1)).first()
        if existing:
            logger.info("种子数据已存在，跳过")
            return

        from core.security import get_password_hash
        import math
        from datetime import datetime as dt_mod, timedelta

        # ════════════════════════════════════════════
        # 1. 充电协议 (3 条)
        # ════════════════════════════════════════════
        protocols = [
            Protocol(id=1, name="DC 250kW", power_kw=250.0, is_fallback=False, description="直流快充"),
            Protocol(id=2, name="DC 20kW", power_kw=20.0, is_fallback=False, description="直流中速"),
            Protocol(id=3, name="AC 7kW", power_kw=7.0, is_fallback=True, description="交流慢充·兜底协议"),
        ]
        for p in protocols:
            session.add(p)
        session.flush()

        # ════════════════════════════════════════════
        # 2. 管理员
        # ════════════════════════════════════════════
        admin = User(
            license_plate="ADMIN",
            user_name="系统管理员",
            password=get_password_hash("admin123"),
            battery_capacity=0, role="admin", balance=0,
        )
        session.add(admin)

        # ════════════════════════════════════════════
        # 3. 车辆用户 (9 个)
        # ════════════════════════════════════════════
        users = []
        battery_map = [60, 60, 60, 80, 80, 80, 100, 100, 100]
        for i in range(9):
            num = f"{i + 1:05d}"
            u = User(
                license_plate=f"京A{num}",
                user_name=num,
                password=get_password_hash("123456"),
                battery_capacity=float(battery_map[i]),
                role="user",
                balance=0,
            )
            session.add(u)
            session.flush()
            # 用户关联全部 3 个协议
            for pid in [1, 2, 3]:
                session.add(UserProtocol(user_id=u.id, protocol_id=pid))
            users.append(u)
        session.flush()

        # ════════════════════════════════════════════
        # 4. 充电桩 (5 个)
        # ════════════════════════════════════════════
        # 快充桩：支持 DC 250kW + AC 7kW
        fast_stations = []
        for name in ["A区-01号快充桩", "A区-02号快充桩"]:
            s = Station(name=name, queue_capacity=5, waiting_capacity=3, charging_capacity=2)
            session.add(s); session.flush()
            for pid in [1, 3]:   # 250kW + 7kW
                session.add(StationProtocol(station_id=s.id, protocol_id=pid))
            fast_stations.append(s)

        # 慢充桩：支持 DC 20kW + AC 7kW
        slow_stations = []
        for name in ["B区-01号慢充桩", "B区-02号慢充桩", "B区-03号慢充桩"]:
            s = Station(name=name, queue_capacity=5, waiting_capacity=3, charging_capacity=2)
            session.add(s); session.flush()
            for pid in [2, 3]:   # 20kW + 7kW
                session.add(StationProtocol(station_id=s.id, protocol_id=pid))
            slow_stations.append(s)

        all_stations = fast_stations + slow_stations
        session.flush()

        # ════════════════════════════════════════════
        # 5. 电价时段 (与原来一致)
        # ════════════════════════════════════════════
        prices_data = [
            ElectricityPrice(period_name="峰时", start_time="08:00", end_time="11:00", price_per_kwh=1.2),
            ElectricityPrice(period_name="平时", start_time="11:00", end_time="18:00", price_per_kwh=0.8),
            ElectricityPrice(period_name="峰时", start_time="18:00", end_time="21:00", price_per_kwh=1.2),
            ElectricityPrice(period_name="谷时", start_time="21:00", end_time="08:00", price_per_kwh=0.4),
        ]
        for ep in prices_data:
            session.add(ep)

        # ════════════════════════════════════════════
        # 6. 服务费阶梯
        # ════════════════════════════════════════════
        session.add(ServiceFeeTier(tier_name="基础阶梯", min_minutes=0, max_minutes=60, rate_per_minute=0.15))
        session.add(ServiceFeeTier(tier_name="超时阶梯", min_minutes=60, max_minutes=None, rate_per_minute=0.20))

        # ════════════════════════════════════════════
        # 7. 全局配置
        # ════════════════════════════════════════════
        session.add(GlobalConfig(config_key="scheduling_algorithm", config_value="shortest_time_single", description="调度算法"))
        session.add(GlobalConfig(config_key="base_service_fee", config_value="5.00", description="基础服务费（元）"))

        session.flush()

        # ════════════════════════════════════════════════════════════
        # 8. 历史充电记录 (2026‑05‑17 ~ 2026‑06‑17, 每车约 10‑14 次)
        # ════════════════════════════════════════════════════════════
        S = 2026, 5, 17
        E = 2026, 6, 17
        start_day = dt_mod(*S, tzinfo=None)
        end_day = dt_mod(*E, tzinfo=None)
        total_days = (end_day - start_day).days  # 31

        def rand_hour(seed: int) -> int:
            """确定性伪随机小时 (0‑23)。"""
            return ((seed * 1103515245 + 12345) // 65536) % 24

        def rand_min(seed: int) -> int:
            return ((seed * 1103515245 + 12346) // 65536) % 60

        session_num = 0
        # 每辆车的累计充电量，粗略模拟
        for ui, u in enumerate(users):
            bat_cap = battery_map[ui]
            # 每辆车 10‑14 次，用余数确定
            count = 10 + (ui * 7 + 3) % 5  # 10~14
            # 在 31 天内均匀分布
            day_positions = [int(total_days * (i + 0.5) / count) for i in range(count)]

            for idx, day_offset in enumerate(day_positions):
                d = start_day + timedelta(days=min(day_offset, total_days - 1))
                hour = rand_hour(session_num + idx * 7 + ui * 13)
                minute = rand_min(session_num + idx * 11 + ui * 17)

                # 选择协议：隔次轮流 — 快充 / 中速 / 基础
                proto_cycle = [(1, 250), (2, 20), (3, 7)]
                pi = (ui + idx) % 3
                proto_id, power_kw = proto_cycle[pi]

                # 选择充电桩：快充协议(1) → 快充桩，慢充协议(2,3) → 慢充桩
                if proto_id == 1:
                    station = fast_stations[(ui + idx) % len(fast_stations)]
                else:
                    station = slow_stations[(ui + idx) % len(slow_stations)]

                # 充电量：电池容量的 15%‑95%，确保多样
                pct = [0.20, 0.35, 0.50, 0.65, 0.80, 0.25, 0.45, 0.70, 0.85, 0.90, 0.30, 0.55, 0.75, 0.95][idx % 14]
                energy = round(bat_cap * pct, 1)
                energy = max(1.0, min(energy, bat_cap * 0.98))  # 不超电池容量

                # 充电时长 (分钟) = energy / power * 60
                charge_min = max(1, int(energy / power_kw * 60))
                # 排队 + 等待约 5‑30 分钟
                queue_min = 5 + (session_num + idx) % 25

                ts_create = d.replace(hour=hour, minute=minute, second=0)
                ts_wait = ts_create + timedelta(minutes=queue_min)
                ts_charge = ts_wait + timedelta(minutes=5 + (session_num + idx) % 20)
                ts_end = ts_charge + timedelta(minutes=charge_min)

                # 创建会话
                cs = ChargingSession(
                    user_id=u.id,
                    station_id=station.id,
                    protocol_id=proto_id,
                    status="completed",
                    zone=None,
                    requested_energy_kwh=energy,
                    charged_energy_kwh=energy,
                    advance_ready=True,
                    queue_position=1,
                    created_at=ts_create,
                    entered_waiting_at=ts_wait,
                    started_charging_at=ts_charge,
                    completed_at=ts_end,
                )
                session.add(cs)
                session.flush()

                # 计算费用
                elec_fee = round(energy * 0.8, 2)  # 平均电价 ~0.8 元/kWh
                base_fee = 5.0
                if charge_min <= 60:
                    time_fee = round(charge_min * 0.15, 2)
                else:
                    time_fee = round(60 * 0.15 + (charge_min - 60) * 0.20, 2)
                svc_fee = round(base_fee + time_fee, 2)
                total_fee = round(elec_fee + svc_fee, 2)

                # 交易流水号
                txn = f"SEED{ts_end.strftime('%Y%m%d%H%M%S')}{cs.id:04d}"

                # 创建账单（已支付）
                bill = Bill(
                    session_id=cs.id,
                    user_id=u.id,
                    station_id=station.id,
                    station_name=station.name,
                    protocol_name={1: "DC 250kW", 2: "DC 20kW", 3: "AC 7kW"}[proto_id],
                    power_kw=power_kw,
                    total_energy_kwh=energy,
                    electricity_fee=elec_fee,
                    base_service_fee=base_fee,
                    time_service_fee=time_fee,
                    service_fee=svc_fee,
                    total_fee=total_fee,
                    charging_minutes=charge_min,
                    status="paid",
                    paid_at=ts_end + timedelta(minutes=1),
                    transaction_id=txn,
                    created_at=ts_end,
                )
                session.add(bill)
                session.flush()

                # 调度日志
                session.add(ScheduleLog(
                    session_id=cs.id,
                    to_station_id=station.id,
                    to_zone="queue",
                    triggered_by="system",
                    detail=f"系统调度到 {station.name}",
                    created_at=ts_create,
                ))
                session.add(ScheduleLog(
                    session_id=cs.id,
                    from_station_id=station.id,
                    from_zone="queue",
                    to_station_id=station.id,
                    to_zone="waiting",
                    triggered_by="system",
                    detail="进入等待区",
                    created_at=ts_wait,
                ))
                session.add(ScheduleLog(
                    session_id=cs.id,
                    from_station_id=station.id,
                    from_zone="waiting",
                    to_station_id=station.id,
                    to_zone="charging",
                    triggered_by="system",
                    detail="开始充电",
                    created_at=ts_charge,
                ))
                session.add(ScheduleLog(
                    session_id=cs.id,
                    from_station_id=station.id,
                    from_zone="charging",
                    to_zone=None,
                    triggered_by="system",
                    detail="充电完成",
                    created_at=ts_end,
                ))

                session_num += 1

        session.commit()
        logger.info("种子数据写入完成（含 %d 条历史充电记录）", session_num)
        system_logger.info("database", f"种子数据写入完成（含 {session_num} 条历史充电记录）")


# ── 延迟导入（避免循环依赖） ──
# 在模块底部导入 model，确保 SQLModel 表类已注册到 metadata
from model.user import User
from model.user_protocol import UserProtocol
from model.station import Station, StationProtocol
from model.protocol import Protocol
from model.session import ChargingSession
from model.bill import Bill
from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
from model.schedule_log import ScheduleLog
from model.log_record import LogRecord
