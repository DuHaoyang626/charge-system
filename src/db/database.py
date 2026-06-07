"""
数据库连接与会话管理

使用 SQLAlchemy 2.0 风格，支持 SQLite。
初始化流程：
    1. init(db_path) — 创建 engine 和 session factory
    2. init_db() — 扫描 ORM 模型并建表
"""

from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeMeta, sessionmaker

from src.utils.logger import logger as log

# ── 全局状态 ───────────────────────────────────────────
engine = None
_SessionFactory: Optional[sessionmaker] = None


def init(db_path: str):
    """初始化数据库连接

    Args:
        db_path: 数据库文件路径，如 "data/charge_system.db"
    """
    global engine, _SessionFactory

    # 确保 data 目录存在
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # SQLite 特定配置
    connect_args = {"check_same_thread": False}  # FastAPI 多线程需要

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args=connect_args,
        echo=False,  # 生产环境关闭 SQL 日志
    )

    _SessionFactory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    log.info("SYSTEM", f"[数据库] SQLite 连接成功 (path: {db_path})")


def init_db():
    """创建所有表（基于 ORM model 定义）"""
    if engine is None:
        raise RuntimeError("数据库未初始化，请先调用 init()")

    # 导入所有 ORM 模型以确保它们被注册到 Base.metadata
    from src.db.models import Base  # noqa: F401

    Base.metadata.create_all(bind=engine)
    log.info("SYSTEM", "[数据库] 所有表已创建")


def get_session():
    """获取一个新的数据库会话（每次调用返回独立会话）"""
    if _SessionFactory is None:
        raise RuntimeError("数据库未初始化，请先调用 init()")
    return _SessionFactory()


def close():
    """关闭数据库连接"""
    global engine, _SessionFactory
    if engine:
        engine.dispose()
        log.info("SYSTEM", "[数据库] 连接已关闭")
    engine = None
    _SessionFactory = None
