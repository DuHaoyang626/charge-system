"""
pytest 全局配置与 fixtures

提供：
1. test_config — 测试专用配置（tests/test_config.yml）
2. test_db — 内存 SQLite 数据库
3. client — FastAPI TestClient
4. service 实例 — AccountService, QueueService 等
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import ConfigLoader
from src.db.models import Base

# ── Fixtures ───────────────────────────────────────────


@pytest.fixture(scope="session")
def test_config():
    """加载测试专用配置"""
    cfg_path = Path(__file__).parent / "test_config.yml"
    loader = ConfigLoader()
    loader.load(cfg_path)
    return loader.settings


@pytest.fixture(scope="function")
def db_session():
    """创建内存 SQLite 数据库会话（函数级，每个测试独立）"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)

    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    yield session

    session.close()
    engine.dispose()


@pytest.fixture(scope="function")
def client(test_config):
    """FastAPI TestClient（函数级，每个测试独立）"""
    from src.main import app

    # 加载测试配置到全局 config 单例
    from src.config import config as global_config
    cfg_path = Path(__file__).parent / "test_config.yml"
    global_config.load(cfg_path)

    with TestClient(app) as c:
        yield c


# ── Service fixtures ───────────────────────────────────


@pytest.fixture(scope="function")
def account_service():
    from src.services import AccountService
    return AccountService()


@pytest.fixture(scope="function")
def queue_service():
    from src.services import QueueService
    return QueueService()


@pytest.fixture(scope="function")
def dispatch_service():
    from src.services import DispatchService
    return DispatchService()


@pytest.fixture(scope="function")
def dispatch_strategy():
    from src.services import DispatchStrategy
    ds = DispatchStrategy()
    ds.init()
    return ds


@pytest.fixture(scope="function")
def billing_service():
    from src.services import BillingService
    return BillingService()


@pytest.fixture(scope="function")
def monitor_service():
    from src.services import MonitorService
    return MonitorService()
