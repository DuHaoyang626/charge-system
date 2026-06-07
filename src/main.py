"""
智能充电桩调度计费系统 — FastAPI 应用入口

启动流程（lifespan）：
    1. ConfigLoader — 读取 application.yml
    2. Logger 初始化（控制台模式）
    3. Database — 连接 SQLite，建表
    4. Logger 开启 DB 通道
    5. 充电桩注册 — 同步配置到 charging_piles 表
    6. 调度策略初始化
    7. FastAPI 启动

启动方式：
    uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.config import config
from src.db.database import close as close_db
from src.db.database import get_session, init as init_db
from src.db.database import init_db as create_tables
from src.routers import account, auth, bills, charging, piles, queues, strategies
from src.utils.logger import logger as log


# ── 生命周期管理 ───────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭生命周期"""
    # ========== 启动阶段 ==========
    # 1. 加载配置
    config.load()
    log.init(
        console_threshold=config.logging.console_threshold,
    )
    log.info("SYSTEM", "[启动] 配置文件加载完成")

    # 2. 初始化数据库
    init_db(config.system.db_path)
    create_tables()
    log.info("SYSTEM", "[启动] 数据库初始化完成")

    # 3. Logger 开启 DB 通道
    log.set_db_ready(get_session)

    # 4. 同步充电桩配置到数据库
    _sync_piles_from_config()
    log.info("SYSTEM", "[启动] 充电桩注册完成")

    # 5. 初始化调度策略
    _init_dispatch_strategy()

    log.info("SYSTEM", f"[启动] 系统就绪 (strategy: {config.dispatch.default_algorithm})")

    yield  # FastAPI 开始处理请求

    # ========== 关闭阶段 ==========
    log.info("SYSTEM", "[关闭] 系统正在关闭...")
    close_db()
    log.info("SYSTEM", "[关闭] 系统已关闭")


# ── FastAPI 应用 ───────────────────────────────────────

app = FastAPI(
    title="智能充电桩调度计费系统",
    description="EV Charging Station Dispatch & Billing System",
    version="0.1.0",
    lifespan=lifespan,
)

# ── 注册路由 ───────────────────────────────────────────

app.include_router(account.router)
app.include_router(auth.router)
app.include_router(charging.router)
app.include_router(bills.router)
app.include_router(piles.router)
app.include_router(queues.router)
app.include_router(strategies.router)


# ── 辅助函数 ───────────────────────────────────────────

def _sync_piles_from_config():
    """将 application.yml 中的充电桩配置同步到 charging_piles 表"""
    from src.db.models import ChargingPile, PileProtocol

    session = get_session()
    try:
        for pile_cfg in config.piles:
            existing = (
                session.query(ChargingPile)
                .filter(ChargingPile.pile_id == pile_cfg.id)
                .first()
            )

            if existing:
                # 更新已有桩
                existing.pile_name = pile_cfg.name
                existing.type = pile_cfg.type
                existing.max_power_kw = pile_cfg.max_power_kw
                existing.parking_spots = pile_cfg.parking_spots
            else:
                # 新增桩
                pile = ChargingPile(
                    pile_id=pile_cfg.id,
                    pile_name=pile_cfg.name,
                    type=pile_cfg.type,
                    max_power_kw=pile_cfg.max_power_kw,
                    parking_spots=pile_cfg.parking_spots,
                )
                session.add(pile)
                log.info("SYSTEM", f"[注册] 新充电桩: {pile_cfg.id} ({pile_cfg.name})")

            # 同步协议
            session.query(PileProtocol).filter(
                PileProtocol.pile_id == pile_cfg.id
            ).delete()

            for proto in pile_cfg.protocols:
                session.add(PileProtocol(pile_id=pile_cfg.id, protocol=proto))

        session.commit()
    except Exception:
        session.rollback()
        log.error("SYSTEM", "[注册] 充电桩同步失败")
        raise
    finally:
        session.close()


def _init_dispatch_strategy():
    """从配置加载默认调度策略（占位，后续实现具体策略类）"""
    log.info(
        "SYSTEM",
        f"[策略] 初始分配策略: {config.dispatch.default_algorithm}, "
        f"故障策略: {config.dispatch.default_fault_strategy}",
    )


# ── 路由 ───────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "智能充电桩调度计费系统 API", "version": "0.1.0"}
