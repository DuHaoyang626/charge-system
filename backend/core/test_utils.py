"""
测试桩工具模块 — 提供数据库测试桩、Mock Session、数据工厂。

用法概览
--------

模式 A — 真实内存数据库（推荐，兼顾速度与保真度）
    with use_in_memory_db() as db:
        # db 是一个真实的 SQLModel Session，运行在内存 SQLite 上
        # 所有 service 层的 engine 自动指向这个内存数据库
        user = UserFactory()
        db.add(user); db.commit(); db.refresh(user)
        result = some_service_function(...)
        assert result ...

模式 B — 直接 Mock（纯单元测试，无需数据库）
    mock_db = MagicMock()
    mock_db.exec.return_value.all.return_value = [mock_data]
    with patch('service.some_module.Session', return_value=mock_db):
        result = some_service_function(...)
        assert result ...

模式 C — FastAPI TestClient 集成测试（自动使用内存数据库）
    client = get_test_client(seed=True)
    resp = client.get("/api/v1/stations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200

切换测试模式：
    默认 conftest.py 使用模式 A（内存 SQLite）
    设置环境变量 CHARGE_TEST_MODE=mock 可切换为模式 B
"""

import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

from sqlmodel import Session, SQLModel, create_engine

# ──────────────────────────────────────────────────────────
# 已知导入了 from core.database import engine 的模块列表
# 在 set_test_engine() 中逐一替换，保证所有 service 层
# 使用同一 test engine
# ──────────────────────────────────────────────────────────
SERVICE_MODULES_WITH_ENGINE = [
    "service.station.service",
    "service.account.service",
    "service.session.service",
    "service.billing.service",
    "service.dispatch.service",
    "service.dispatch.strategy",
    "service.queue.service",
    "service.queue.admin_service",
    "service.admin.service",
    "scheduler.dispatch_loop",
]


def set_test_engine(test_engine) -> None:
    """
    将 test_engine 注入到 core.database 以及所有已导入的 service 模块。

    调用后，所有 service 层的 with Session(engine) as db 会使用 test_engine。
    需要在测试开始时调用，测试结束后调用 restore_engines()。
    """
    import core.database

    core.database.engine = test_engine

    # 替换已导入模块中的 engine 引用
    for mod_name in SERVICE_MODULES_WITH_ENGINE:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "engine"):
            mod.engine = test_engine


def restore_engines() -> None:
    """恢复所有模块的 engine 为 core.database 的当前值（测试 teardown 时调用）。"""
    import core.database

    default_engine = getattr(core.database, "_default_engine", core.database.engine)
    core.database.engine = default_engine
    for mod_name in SERVICE_MODULES_WITH_ENGINE:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "engine"):
            mod.engine = default_engine


# ──────────────────────────────────────────────────────────
# 内存数据库
# ──────────────────────────────────────────────────────────


def create_in_memory_engine():
    """
    创建一个 SQLite 内存 engine，建好所有表。

    使用 StaticPool 确保所有 Session 共享同一个内存数据库
    （SQLite 默认 :memory: 对不同连接会创建独立数据库）。
    """
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine


@contextmanager
def use_in_memory_db():
    """
    上下文管理器：创建内存 SQLite 数据库，注入到所有 service 模块。

    进入时返回一个 Session；退出时恢复所有 engine。
    用法：
        with use_in_memory_db() as db:
            # db 是 Session（已绑内存数据库）
            # service 模块的 engine 自动指向内存数据库
            do_test(db)
    """
    engine = create_in_memory_engine()
    set_test_engine(engine)
    try:
        with Session(engine) as session:
            yield session
    finally:
        restore_engines()


# ──────────────────────────────────────────────────────────
# FastAPI TestClient 集成测试助手
# ──────────────────────────────────────────────────────────


def get_test_client(seed: bool = False):
    """
    返回一个使用内存数据库的 FastAPI TestClient。
    可选 seed=True 灌入种子数据。

    用法：
        client = get_test_client(seed=True)
        resp = client.get("/api/v1/stations", ...)
    """
    from fastapi.testclient import TestClient

    # 创建并注入内存 engine
    test_engine = create_in_memory_engine()
    set_test_engine(test_engine)

    # 灌种子数据
    if seed:
        from core.database import init_db as _real_init

        _real_init()

    # 延迟导入 main.app，确保此时 engine 已被替换
    from main import app

    client = TestClient(app)

    # 把 engine 和 client 一起返回，方便测试结束后清理
    client._test_engine = test_engine
    return client


def close_test_client(client) -> None:
    """测试结束后恢复 engine。"""
    restore_engines()


# ──────────────────────────────────────────────────────────
# 数据模型工厂 — 快速创建测试数据
# ──────────────────────────────────────────────────────────


def UserFactory(**overrides: Any) -> dict:
    """
    创建 User 模型实例的工厂函数。
    返回一个 dict，可直接作为关键字参数传给 User(**dict)。
    """
    import hashlib

    uid = overrides.get("id", id(overrides))
    raw_plate = overrides.get("license_plate", f"测试-车牌-{abs(hash(str(uid))) % 100000:05d}")
    return {
        "license_plate": raw_plate,
        "user_name": overrides.get("user_name", "测试用户"),
        "password": overrides.get("password", "$2b$12$fakehash"),
        "phone": overrides.get("phone", None),
        "battery_capacity": overrides.get("battery_capacity", 60.0),
        "role": overrides.get("role", "user"),
        "balance": overrides.get("balance", 0),
        "priority": overrides.get("priority", 0),
    }


def StationFactory(**overrides: Any) -> dict:
    """创建 Station 模型实例的工厂函数。"""
    return {
        "name": overrides.get("name", f"测试桩-{abs(hash(str(overrides))) % 1000:03d}"),
        "status": overrides.get("status", "running"),
        "queue_capacity": overrides.get("queue_capacity", 10),
        "waiting_capacity": overrides.get("waiting_capacity", 5),
        "charging_capacity": overrides.get("charging_capacity", 3),
        "queue_count": overrides.get("queue_count", 0),
        "waiting_count": overrides.get("waiting_count", 0),
        "charging_count": overrides.get("charging_count", 0),
        "base_service_fee": overrides.get("base_service_fee", 5.0),
    }


def ProtocolFactory(**overrides: Any) -> dict:
    """创建 Protocol 模型实例的工厂函数。"""
    return {
        "name": overrides.get("name", "DC 测试kW"),
        "power_kw": overrides.get("power_kw", 60.0),
        "is_fallback": overrides.get("is_fallback", False),
        "description": overrides.get("description", "测试协议"),
    }


def SessionFactory(**overrides: Any) -> dict:
    """创建 ChargingSession 模型实例的工厂函数。"""
    now = datetime.utcnow()
    return {
        "user_id": overrides.get("user_id", 1),
        "station_id": overrides.get("station_id", 1),
        "protocol_id": overrides.get("protocol_id", 1),
        "status": overrides.get("status", "queued"),
        "zone": overrides.get("zone", "queue"),
        "requested_energy_kwh": overrides.get("requested_energy_kwh", 30.0),
        "charged_energy_kwh": overrides.get("charged_energy_kwh", 0.0),
        "advance_ready": overrides.get("advance_ready", False),
        "queue_position": overrides.get("queue_position", 1),
        "created_at": overrides.get("created_at", now),
        "entered_waiting_at": overrides.get("entered_waiting_at", None),
        "started_charging_at": overrides.get("started_charging_at", None),
        "completed_at": overrides.get("completed_at", None),
    }


def BillFactory(**overrides: Any) -> dict:
    """创建 Bill 模型实例的工厂函数。"""
    return {
        "session_id": overrides.get("session_id", 1),
        "user_id": overrides.get("user_id", 1),
        "station_id": overrides.get("station_id", 1),
        "station_name": overrides.get("station_name", "测试桩"),
        "protocol_name": overrides.get("protocol_name", "DC 测试kW"),
        "power_kw": overrides.get("power_kw", 60.0),
        "total_energy_kwh": overrides.get("total_energy_kwh", 30.0),
        "electricity_fee": overrides.get("electricity_fee", 24.0),
        "base_service_fee": overrides.get("base_service_fee", 5.0),
        "time_service_fee": overrides.get("time_service_fee", 4.5),
        "service_fee": overrides.get("service_fee", 9.5),
        "total_fee": overrides.get("total_fee", 33.5),
        "charging_minutes": overrides.get("charging_minutes", 30),
        "status": overrides.get("status", "unpaid"),
        "paid_at": overrides.get("paid_at", None),
        "transaction_id": overrides.get("transaction_id", None),
    }


# ──────────────────────────────────────────────────────────
# 内存数据库种子辅助 — 快速将工厂数据写入数据库
# ──────────────────────────────────────────────────────────


def seed_db_with_factories(db: Session, **model_lists) -> list[Any]:
    """
    用工厂 dict 批量创建模型实例并写入数据库。

    用法：
        with use_in_memory_db() as db:
            users = seed_db_with_factories(
                db,
                User=[UserFactory(role="user"), UserFactory(role="admin")],
                Protocol=[ProtocolFactory(name="DC 100kW", power_kw=100)],
            )
            # users 是 [User, User] 已写入数据库
    """
    from model.user import User
    from model.station import Station, StationProtocol
    from model.protocol import Protocol
    from model.session import ChargingSession
    from model.bill import Bill

    MODEL_MAP = {
        "User": User,
        "Station": Station,
        "StationProtocol": StationProtocol,
        "Protocol": Protocol,
        "ChargingSession": ChargingSession,
        "Bill": Bill,
    }

    created: list[Any] = []
    for model_key, factories in model_lists.items():
        model_cls = MODEL_MAP.get(model_key)
        if model_cls is None:
            raise ValueError(f"未知模型: {model_key}，可用: {list(MODEL_MAP.keys())}")
        for factory_kwargs in factories:
            instance = model_cls(**factory_kwargs)
            db.add(instance)
            db.flush()
            db.refresh(instance)
            created.append(instance)

    db.commit()
    return created


# ──────────────────────────────────────────────────────────
# Mock Session 辅助 — 用于纯单元测试（不需要数据库）
# ──────────────────────────────────────────────────────────


def make_mock_db(**defaults: Any) -> MagicMock:
    """
    创建一个模拟的 Session 对象，用于纯单元测试。

    mock_db.exec().all() 返回预设列表
    mock_db.exec().first() 返回预设第一条
    mock_db.get(Model, id) 返回预设对象

    用法：
        mock_db = make_mock_db()
        mock_db.get.return_value = User(id=1, ...)
        mock_db.exec.return_value.all.return_value = [Protocol(...)]
    """
    mock_db = MagicMock(spec=Session)
    mock_db.exec.return_value.all.return_value = []
    mock_db.exec.return_value.first.return_value = None
    mock_db.get.return_value = None
    return mock_db


@contextmanager
def patch_engine_in_module(module_path: str, test_engine):
    """
    在指定模块中 patch engine 变量。
    如果模块未导入则跳过。
    """
    mod = sys.modules.get(module_path)
    if mod is None:
        yield
        return
    original = getattr(mod, "engine", None)
    setattr(mod, "engine", test_engine)
    try:
        yield
    finally:
        if original is not None:
            setattr(mod, "engine", original)
        else:
            delattr(mod, "engine")


@contextmanager
def patch_all_engines(test_engine):
    """
    Patch 所有已知 service 模块的 engine 引用 + core.database.engine。
    """
    import core.database

    original_db = getattr(core.database, "engine", None)
    core.database.engine = test_engine

    patches = []
    for mod_name in SERVICE_MODULES_WITH_ENGINE:
        mod = sys.modules.get(mod_name)
        if mod is not None and hasattr(mod, "engine"):
            original = mod.engine
            mod.engine = test_engine
            patches.append((mod, original))

    try:
        yield
    finally:
        for mod, original in patches:
            mod.engine = original
        if original_db is not None:
            core.database.engine = original_db
