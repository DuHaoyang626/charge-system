"""
数据库连接 — engine + init_db + 种子数据。

在应用 lifecycle 启动时调用 init_db() 自动建表并灌入初始数据。
"""

import logging

from sqlmodel import SQLModel, Session, create_engine, select

from core.config import settings

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
    _seed_initial_data()
    logger.info("数据库初始化完成")


# ──────────────────────────────────────────────
# 种子数据
# ──────────────────────────────────────────────


def _seed_initial_data() -> None:
    """
    灌初始数据：
    - 5 条充电协议
    - 1 个管理员账号
    - 2 台演示充电桩 + 协议关联
    - 4 条电价配置
    - 2 条服务费阶梯
    - 2 条全局配置项
    """
    with Session(engine) as session:
        # 检查是否已有数据（以 protocols 表是否有记录为准）
        existing = session.exec(select(Protocol).limit(1)).first()
        if existing:
            logger.info("种子数据已存在，跳过")
            return

        # ── 1. 充电协议 ──
        protocols = [
            Protocol(name="AC 7kW", power_kw=7.0, is_fallback=True, description="交流慢充·兜底协议"),
            Protocol(name="DC 22kW", power_kw=22.0, is_fallback=False, description=None),
            Protocol(name="DC 50kW", power_kw=50.0, is_fallback=False, description=None),
            Protocol(name="DC 120kW", power_kw=120.0, is_fallback=False, description=None),
            Protocol(name="DC 250kW", power_kw=250.0, is_fallback=False, description=None),
        ]
        for p in protocols:
            session.add(p)
        session.flush()  # 获得 protocols 的 id

        # ── 2. 管理员账号 ──
        from core.security import get_password_hash

        admin = User(
            license_plate="ADMIN",
            user_name="系统管理员",
            password=get_password_hash("admin123"),
            battery_capacity=0,
            role="admin",
            balance=0,
        )
        session.add(admin)

        # ── 3. 演示充电桩 ──
        station_a = Station(
            name="A区-01号桩",
            queue_capacity=5,
            waiting_capacity=3,
            charging_capacity=2,
        )
        session.add(station_a)
        session.flush()

        station_b = Station(
            name="B区-02号桩",
            queue_capacity=5,
            waiting_capacity=3,
            charging_capacity=2,
        )
        session.add(station_b)
        session.flush()

        # 关联协议：两个桩都支持 AC 7kW (id=1) + DC 50kW (id=3) + DC 120kW (id=4)
        # protocols 的 id 按添加顺序为 1~5
        for sid in [station_a.id, station_b.id]:
            for pid in [1, 3, 4]:
                session.add(StationProtocol(station_id=sid, protocol_id=pid))

        # ── 4. 电价时段 ──
        prices = [
            ElectricityPrice(period_name="峰时", start_time="08:00", end_time="11:00", price_per_kwh=1.2, priority=1),
            ElectricityPrice(period_name="平时", start_time="11:00", end_time="18:00", price_per_kwh=0.8, priority=2),
            ElectricityPrice(period_name="峰时", start_time="18:00", end_time="21:00", price_per_kwh=1.2, priority=3),
            ElectricityPrice(period_name="谷时", start_time="21:00", end_time="08:00", price_per_kwh=0.4, priority=4),
        ]
        for ep in prices:
            session.add(ep)

        # ── 5. 服务费阶梯 ──
        tiers = [
            ServiceFeeTier(tier_name="基础阶梯", min_minutes=0, max_minutes=60, rate_per_minute=0.15),
            ServiceFeeTier(tier_name="超时阶梯", min_minutes=60, max_minutes=None, rate_per_minute=0.20),
        ]
        for t in tiers:
            session.add(t)

        # ── 6. 全局配置 ──
        configs = [
            GlobalConfig(
                config_key="scheduling_algorithm",
                config_value="shortest_time_single",
                description="调度算法",
            ),
            GlobalConfig(
                config_key="base_service_fee",
                config_value="5.00",
                description="基础服务费（元）",
            ),
        ]
        for c in configs:
            session.add(c)

        session.commit()
        logger.info("种子数据写入完成")


# ── 延迟导入（避免循环依赖） ──
# 在模块底部导入 model，确保 SQLModel 表类已注册到 metadata
from model.user import User
from model.station import Station, StationProtocol
from model.protocol import Protocol
from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
