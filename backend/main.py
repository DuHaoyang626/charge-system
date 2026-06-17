"""
智能充电桩调度计费系统 — 应用入口

启动方式：
    python main.py --log_level info
    # 或 uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level info
"""

import argparse
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import init_db
from core.exception_handlers import app_exception_handler
from core.exceptions import AppException
from core.logger import system_logger
from scheduler.dispatch_loop import DispatchLoop

# ── 日志等级参数解析 ──
_LOG_LEVEL_HELP = "日志等级: debug / info / warning / error（默认 info）"

parser = argparse.ArgumentParser(description="智能充电桩调度计费系统")
parser.add_argument("--log_level", type=str, default=None, help=_LOG_LEVEL_HELP)
args, _ = parser.parse_known_args()

# 优先级：命令行参数 > 环境变量 > 默认 info
log_level_str = args.log_level or os.getenv("CHARGE_SYSTEM_LOG_LEVEL", "info")
log_level_numeric = getattr(logging, log_level_str.upper(), logging.INFO)

logging.basicConfig(level=log_level_numeric)
logger = logging.getLogger("charge-system")

# 同步 system_logger 的等级
system_logger.set_level(log_level_numeric)
logger.info("日志等级设置为: %s", log_level_str.upper())

dispatch_loop = DispatchLoop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时
    logger.info("正在初始化数据库...")
    init_db()
    logger.info("数据库初始化完成，正在启动调度循环...")
    asyncio.create_task(_startup())
    yield
    # 关闭时
    logger.info("正在停止调度循环...")
    await dispatch_loop.stop()
    logger.info("应用已关闭")


async def _startup():
    """延迟启动调度循环，等待数据库就绪。"""
    await asyncio.sleep(2)
    await dispatch_loop.start()


app = FastAPI(
    title="智能充电桩调度计费系统",
    description="基于 FastAPI + SQLModel 的充电桩调度计费后端 API",
    version="0.1.0",
    lifespan=lifespan,
)

# 注册全局异常处理器
app.add_exception_handler(AppException, app_exception_handler)


# ──────────────────────────────────────────────
# 注册路由
# ──────────────────────────────────────────────

from api.auth.router import router as auth_router
from api.users.router import router as users_router
from api.protocols.router import router as protocol_router
from api.stations.router import router as station_router
from api.sessions.router import router as session_router
from api.bills.router import router as bill_router
from api.admin.config.router import router as admin_config_router
from api.admin.stations.router import router as admin_station_router
from api.admin.sessions.router import router as admin_session_router
from api.admin.bills.router import router as admin_bill_router
from api.admin.queues.router import router as admin_queue_router
from api.admin.reports.router import router as admin_report_router
from api.admin.logs.router import router as admin_logs_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(protocol_router, prefix="/api/v1")
app.include_router(station_router, prefix="/api/v1")
app.include_router(session_router, prefix="/api/v1")
app.include_router(bill_router, prefix="/api/v1")
app.include_router(admin_config_router, prefix="/api/v1")
app.include_router(admin_station_router, prefix="/api/v1")
app.include_router(admin_session_router, prefix="/api/v1")
app.include_router(admin_bill_router, prefix="/api/v1")
app.include_router(admin_queue_router, prefix="/api/v1")
app.include_router(admin_report_router, prefix="/api/v1")
app.include_router(admin_logs_router, prefix="/api/v1")


# ── 根路径健康检查 ──

@app.get("/")
async def root():
    return {"message": "智能充电桩调度计费系统", "version": "0.1.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
