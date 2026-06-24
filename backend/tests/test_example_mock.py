"""
测试桩使用示例 — 展示三种测试方式。

运行：
    pytest tests/test_example_mock.py -v

方式 A：in_memory_db fixture（推荐）
    使用内存 SQLite 数据库，速度快且保真度高。
    所有 service 层自动使用该数据库。

方式 B：MockClient / 依赖覆盖
    测试 HTTP 接口层，使用内存数据库。

方式 C：直接 Mock Session（纯单元测试）
    用 unittest.mock 模拟数据库，不依赖 SQLite。

方式 D：seed_db_with_factories 工厂函数
    快速批量构建测试数据。
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════════════
# A. 使用 in_memory_db fixture（推荐方式）
# ══════════════════════════════════════════════════════════


class TestWithInMemoryDB:
    """展示如何使用内存数据库进行 service 层单元测试。"""

    def test_account_service_register(self, in_memory_db):
        """注册服务：使用内存数据库测试完整注册流程。"""
        from model.protocol import Protocol

        # Arrange — 准备测试数据（协议必须存在）
        proto = Protocol(id=1, name="DC 250kW", power_kw=250.0)
        in_memory_db.add(proto)
        in_memory_db.commit()

        # Act — 调用 service（自动使用内存数据库）
        from service.account.service import register

        result = register(
            license_plate="测试-001",
            user_name="测试车辆",
            battery_capacity=60.0,
            password="test123",
            protocol_ids=[1],
        )

        # Assert
        assert result["licensePlate"] == "测试-001"
        assert "token" in result
        assert result["userId"] is not None

    def test_station_service_list(self, in_memory_db):
        """充电桩服务：测试查询逻辑。"""
        from model.station import Station, StationProtocol
        from model.protocol import Protocol

        # Arrange
        proto = Protocol(id=1, name="DC 250kW", power_kw=250.0)
        in_memory_db.add(proto)
        station = Station(
            name="测试桩-001",
            queue_capacity=5,
            waiting_capacity=3,
            charging_capacity=2,
        )
        in_memory_db.add(station)
        in_memory_db.commit()
        sp = StationProtocol(station_id=station.id, protocol_id=1)
        in_memory_db.add(sp)
        in_memory_db.commit()

        # Act
        from service.station.service import list_stations

        result = list_stations()

        # Assert
        assert len(result["stations"]) == 1
        assert result["stations"][0]["name"] == "测试桩-001"
        assert len(result["stations"][0]["supportedProtocols"]) == 1

    def test_billing_engine_directly(self, in_memory_db):
        """
        计费引擎：纯函数计算，不需要数据库。
        注意传入的 start/end 是 UTC 时间，引擎内部会转为北京时间（+8h）。
        UTC 00:00~03:00 → BJT 08:00~11:00 → 峰时电价 1.2 元/kWh
        """
        from service.billing.engine import (
            PriceSlot,
            ServiceTier,
            calculate_electricity_fee,
            calculate_service_fee,
        )

        # 电费计算：UTC 00:00~03:00 → BJT 08:00~11:00 全部在峰时
        prices = [
            PriceSlot(period_name="谷时", start_time="00:00", end_time="08:00", price_per_kwh=0.4),
            PriceSlot(period_name="峰时", start_time="08:00", end_time="11:00", price_per_kwh=1.2),
        ]
        start = datetime(2026, 6, 1, 0, 0, 0)  # UTC → BJT 08:00
        end = datetime(2026, 6, 1, 3, 0, 0)    # UTC → BJT 11:00

        result = calculate_electricity_fee(start, end, total_energy_kwh=50, prices=prices)
        # 全部在峰时：50 × 1.2 = 60 元
        assert result.total == 60.0

        # 服务费计算：30 分钟 + 基础服务费 5 元
        tiers = [
            ServiceTier(tier_name="基础阶梯", min_minutes=0, max_minutes=60, rate_per_minute=0.15),
        ]
        svc = calculate_service_fee(charging_minutes=30, base_fee=5.0, tiers=tiers)
        assert svc.total == 9.5  # 5 + 30 × 0.15


# ══════════════════════════════════════════════════════════
# B. 使用 mock_client / seeded_client（HTTP 接口层测试）
# ══════════════════════════════════════════════════════════


class TestWithMockClient:
    """展示如何使用内存数据库 TestClient 测试 HTTP 接口。"""

    def test_health_endpoint(self, mock_client):
        """健康检查接口（无需数据库）。"""
        resp = mock_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_root_endpoint(self, mock_client):
        """根路径接口。"""
        resp = mock_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "running"
        assert "version" in data

    def test_auth_login_nonexistent(self, mock_client):
        """登录不存在用户（无需种子数据）。"""
        resp = mock_client.post("/api/v1/auth/login", json={
            "licensePlate": "不存在的用户",
            "password": "xxx",
        })
        assert resp.status_code == 400

    def test_auth_no_token(self, mock_client):
        """未登录访问受保护接口。"""
        resp = mock_client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_seeded_client_stations(self, seeded_client):
        """
        种子数据模式下查询充电桩。
        注意：seeded_client 有独立数据库，需要在测试内获取 token。
        """
        # 使用种子数据中的管理员账号登录
        login_resp = seeded_client.post("/api/v1/auth/login", json={
            "licensePlate": "ADMIN",
            "password": "admin123",
        })
        token = login_resp.json()["data"]["token"]

        # 查询充电桩列表
        resp = seeded_client.get("/api/v1/stations",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["stations"]) >= 5  # 种子有 5 个桩


# ══════════════════════════════════════════════════════════
# C. 直接 Mock Session（纯单元测试，最轻量）
# ══════════════════════════════════════════════════════════


class TestWithDirectMock:
    """展示如何使用 unittest.mock 进行纯单元测试（无需数据库）。"""

    def test_dispatch_strategy_import(self):
        """调度策略：纯算法逻辑测试，不需要数据库。"""
        from service.dispatch.strategy import get_strategy

        strategy = get_strategy("shortest_time_single")
        assert strategy is not None
        from service.dispatch.strategy import ShortestTimeSingleStrategy
        assert isinstance(strategy, ShortestTimeSingleStrategy)

    def test_account_crypto(self):
        """密码哈希 + JWT — 不依赖数据库。"""
        from core.security import (
            create_access_token,
            get_password_hash,
            verify_password,
            verify_token,
        )

        # 密码哈希
        hashed = get_password_hash("test123")
        assert verify_password("test123", hashed)
        assert not verify_password("wrong", hashed)

        # JWT 签发与验签
        token = create_access_token(user_id=42, role="user")
        payload = verify_token(token)
        assert payload is not None
        assert payload["user_id"] == 42
        assert payload["role"] == "user"

    def test_exception_handling(self):
        """异常处理 — 纯逻辑，不需要数据库。"""
        from core.exceptions import AppException, Err

        exc = AppException(*Err.NOT_FOUND)
        assert exc.code == 404
        assert exc.message == "资源不存在"

        exc2 = AppException(*Err.UNAUTHORIZED)
        assert exc2.code == 401

    def test_station_list_with_mock_session(self):
        """
        充电桩列表：完全 mock 数据库 Session。

        注意：list_stations() 内部调用了 _get_station_protocols()，
        它做了 join 查询，所以 exec().all() 需要返回元组列表。
        """
        from model.station import Station
        from model.protocol import Protocol

        # 准备 mock 数据
        mock_station = Station(
            id=1, name="Mock桩-001", status="running",
            queue_capacity=5, waiting_capacity=3, charging_capacity=2,
            queue_count=0, waiting_count=0, charging_count=0,
            base_service_fee=5.0,
        )

        mock_db = MagicMock()

        # 第一个 exec().all() 调用：SELECT Station → 返回桩列表
        # 第二个 exec().all() 调用：SELECT StationProtocol, Protocol JOIN → 返回协议
        call_results = [
            [mock_station],                          # 第一次 all() → stations
            [(MagicMock(), Protocol(                  # 第二次 all() → protocols
                id=1, name="DC 250kW", power_kw=250.0
            ))],
        ]
        mock_db.exec.return_value.all.side_effect = call_results
        # get(Station, id) → 用于 detail
        mock_db.get.return_value = mock_station

        with patch("service.station.service.Session") as mock_session_cls, \
             patch("service.station.service.engine", MagicMock()):
            mock_session_cls.return_value.__enter__.return_value = mock_db
            from service.station.service import list_stations

            result = list_stations()

        assert len(result["stations"]) == 1
        assert result["stations"][0]["name"] == "Mock桩-001"
        assert result["stations"][0]["status"] == "running"

    def test_queue_enqueue_logic(self):
        """
        排队入队逻辑：直接 mock 数据库 Session。

        enqueue() 接受 db 参数（共享 session），适合纯逻辑测试。
        """
        from service.queue.service import enqueue
        from model.session import ChargingSession
        from model.station import Station
        from core.exceptions import AppException

        # 准备 mock 桩
        mock_station = MagicMock(spec=Station)
        mock_station.id = 1
        mock_station.status = "running"
        mock_station.queue_count = 2
        mock_station.queue_capacity = 10
        mock_station.name = "Mock桩"

        mock_db = MagicMock()
        mock_db.get.return_value = mock_station

        mock_session = MagicMock(spec=ChargingSession)
        mock_session.id = 99

        # 执行
        position = enqueue(mock_db, mock_session, mock_station)

        # 验证：排队位置 = 当前排队数 + 1
        assert position == 3
        # 验证桩的排队计数增加
        assert mock_station.queue_count == 3
        # 验证更新了充电会话属性
        assert mock_session.station_id == 1
        assert mock_session.status == "queued"
        assert mock_session.queue_position == 3

    def test_queue_enqueue_full(self):
        """排队区已满时抛出异常。"""
        from service.queue.service import enqueue
        from model.session import ChargingSession
        from model.station import Station
        from core.exceptions import AppException

        mock_station = MagicMock(spec=Station)
        mock_station.id = 1
        mock_station.status = "running"
        mock_station.queue_count = 10
        mock_station.queue_capacity = 10

        mock_db = MagicMock()
        mock_db.get.return_value = mock_station

        mock_session = MagicMock(spec=ChargingSession)

        with pytest.raises(AppException) as exc_info:
            enqueue(mock_db, mock_session, mock_station)
        assert "排队区已满" in str(exc_info.value.message)

    def test_exceptions_with_mock(self):
        """测试 service 层异常路径。"""
        from service.station.service import get_station_detail
        from core.exceptions import AppException

        with patch("service.station.service.Session") as mock_session_cls, \
             patch("service.station.service.engine", MagicMock()):
            mock_db = MagicMock()
            mock_db.get.return_value = None  # 充电桩不存在
            mock_session_cls.return_value.__enter__.return_value = mock_db

            with pytest.raises(AppException) as exc_info:
                get_station_detail(station_id=999)

            assert exc_info.value.code == 404


# ══════════════════════════════════════════════════════════
# D. 使用 seed_db_with_factories 快速构建数据
# ══════════════════════════════════════════════════════════


class TestWithFactories:
    """展示如何使用工厂函数快速构建测试数据。"""

    def test_seed_factories(self, in_memory_db):
        """使用 seed_db_with_factories 快速灌入测试数据。"""
        from core.test_utils import (
            UserFactory,
            StationFactory,
            ProtocolFactory,
            seed_db_with_factories,
        )

        # 批量创建
        created = seed_db_with_factories(
            in_memory_db,
            User=[
                UserFactory(license_plate="工厂-001", role="user"),
                UserFactory(license_plate="工厂-002", role="user"),
            ],
            Protocol=[
                ProtocolFactory(name="DC 100kW", power_kw=100),
                ProtocolFactory(name="AC 7kW", power_kw=7, is_fallback=True),
            ],
            Station=[
                StationFactory(name="工厂桩-001"),
            ],
        )

        # 验证写入
        from sqlmodel import select
        from model.user import User

        users = in_memory_db.exec(select(User)).all()
        assert len(users) == 2
        assert users[0].license_plate == "工厂-001"

        from model.station import Station

        stations = in_memory_db.exec(select(Station)).all()
        assert len(stations) == 1
