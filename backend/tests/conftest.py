"""
pytest 配置 — 支持两种测试模式：

模式 A — 真实临时文件 SQLite（默认，兼容现有测试）
    每次测试会话自动创建临时数据库，重建 schema。
    通过 DATABASE_URL 环境变量切换数据库路径。

模式 B — 内存 Mock 数据库（快速单测）
    使用 in_memory_db fixture，无需磁盘 I/O。
    设置 CHARGE_TEST_MODE=mock 环境变量可切换默认 fixture 行为。

模式切换：
    1. 环境变量：CHARGE_TEST_MODE=mock pytest tests/ -v
    2. Fixture 级别：在测试函数参数中直接使用 mock_db 或 real_db fixture
"""

import os
import tempfile

# ── 模式 A: 默认使用临时文件 SQLite ──
_tmp_dir = tempfile.mkdtemp()
_db_path = os.path.join(_tmp_dir, "test_charge_system.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

# 此时再导入 core.database 会使用新的 URL 创建 engine
from core.database import init_db

init_db()

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from core.database import engine
from main import app


# ──────────────────────────────────────────────
# 公共 Fixtures
# ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def db_engine():
    """全局测试数据库 engine（session 级，自动使用临时 SQLite）。"""
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    提供一次性的数据库 Session（函数级，自动事务回滚）。
    每个测试函数获得一个干净的 Session，测试结束后自动回滚。
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client():
    """
    提供 TestClient 实例（函数级）。
    每个测试函数获得一个干净的 TestClient，自动使用测试数据库。
    """
    return TestClient(app)


# ──────────────────────────────────────────────
# Mock / 内存数据库模式 Fixtures
# ──────────────────────────────────────────────


@pytest.fixture(scope="function")
def in_memory_db():
    """
    提供内存 SQLite 数据库 Session（函数级）。
    速度快，无需磁盘 I/O，适合纯逻辑单测。
    所有 service 层的 engine 自动指向该内存数据库。

    用法：
        def test_something(in_memory_db):
            from model.user import User
            user = User(license_plate="test", ...)
            in_memory_db.add(user)
            in_memory_db.commit()
            ...
    """
    from core.test_utils import use_in_memory_db

    with use_in_memory_db() as session:
        yield session


@pytest.fixture(scope="function")
def mock_client(in_memory_db):
    """
    基于内存数据库的 TestClient（函数级）。
    每个测试函数独立，互不干扰。

    用法：
        def test_api(mock_client):
            resp = mock_client.get("/health")
            assert resp.status_code == 200
    """
    return TestClient(app)


@pytest.fixture(scope="function")
def seeded_client():
    """
    基于内存数据库的 TestClient（函数级），含种子数据。

    用法：
        def test_list_stations(seeded_client, admin_token):
            resp = seeded_client.get("/api/v1/stations",
                headers={"Authorization": f"Bearer {admin_token}"})
            assert resp.status_code == 200
    """
    from core.test_utils import get_test_client

    client = get_test_client(seed=True)
    yield client
    from core.test_utils import close_test_client

    close_test_client(client)


# ──────────────────────────────────────────────
# Token Fixtures
# ──────────────────────────────────────────────


@pytest.fixture(scope="session")
def admin_token_raw():
    """登录 ADMIN 账号获取 token（session 级）。"""
    resp = TestClient(app).post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN",
        "password": "admin123",
    })
    return resp.json()["data"]["token"]


@pytest.fixture(scope="function")
def admin_token(admin_token_raw):
    return admin_token_raw


@pytest.fixture(scope="session")
def user_token_raw():
    """注册 + 登录一个测试用户并获取 token（session 级）。"""
    client = TestClient(app)
    import random

    plate = f"测试-{random.randint(10000, 99999)}"
    client.post("/api/v1/auth/register", json={
        "licensePlate": plate,
        "userName": "测试用户",
        "batteryCapacity": 60.0,
        "password": "test123456",
        "confirmPassword": "test123456",
        "protocolIds": [1, 3],
    })
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": plate,
        "password": "test123456",
    })
    return resp.json()["data"]["token"]


@pytest.fixture(scope="function")
def user_token(user_token_raw):
    return user_token_raw
