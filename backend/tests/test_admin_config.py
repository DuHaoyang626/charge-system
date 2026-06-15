"""
P0-01/P0-02 验证：配置管理接口 — 严格遵循 API 接口说明。

测试覆盖：
  - GET /admin/config 返回结构符合 API 文档
  - PUT /admin/config 接受扁平请求并正确更新
  - 电价时段冲突校验
  - 字段完整性校验

运行：pytest tests/test_admin_config.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.config import ElectricityPrice, ServiceFeeTier, GlobalConfig

client = TestClient(app)


def _admin_token() -> str:
    """获取管理员 JWT token。"""
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN",
        "password": "admin123",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def _user_token() -> str:
    """获取普通用户 token。"""
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "京A12345",
        "password": "abc123456",
    })
    if resp.status_code == 200:
        return resp.json()["data"]["token"]
    # 先注册
    client.post("/api/v1/auth/register", json={
        "licensePlate": "京A12345", "userName": "测试车",
        "batteryCapacity": 60.0, "password": "abc123456",
        "confirmPassword": "abc123456", "protocolIds": [1],
    })
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "京A12345", "password": "abc123456",
    })
    return resp.json()["data"]["token"]


class TestGetConfig:
    """GET /admin/config"""

    def test_get_config_structure(self):
        """返回结构严格遵循 API 接口说明。"""
        token = _admin_token()
        resp = client.get("/api/v1/admin/config", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()["data"]

        # 顶层字段
        assert "schedulingAlgorithm" in data
        assert "baseServiceFee" in data
        assert isinstance(data["schedulingAlgorithm"], str)
        assert isinstance(data["baseServiceFee"], (int, float))

        # electricityPrices — 字段名为 periodName / start / end / pricePerKwh
        assert "electricityPrices" in data
        assert isinstance(data["electricityPrices"], list)
        if data["electricityPrices"]:
            p = data["electricityPrices"][0]
            assert "periodName" in p
            assert "start" in p          # 不是 startTime
            assert "end" in p            # 不是 endTime
            assert "pricePerKwh" in p
            assert "id" not in p         # 不能有 id
            assert "priority" not in p   # 不能有 priority

        # serviceFeeTiers — 字段名为 minMinutes / maxMinutes / ratePerMinute
        assert "serviceFeeTiers" in data
        assert isinstance(data["serviceFeeTiers"], list)
        if data["serviceFeeTiers"]:
            t = data["serviceFeeTiers"][0]
            assert "minMinutes" in t
            assert "maxMinutes" in t
            assert "ratePerMinute" in t
            assert "id" not in t         # 不能有 id

    def test_get_config_requires_admin(self):
        """普通用户无权访问。"""
        token = _user_token()
        resp = client.get("/api/v1/admin/config", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 403

    def test_get_config_no_auth(self):
        """未认证返回 401。"""
        resp = client.get("/api/v1/admin/config")
        assert resp.status_code == 401


class TestUpdateConfig:
    """PUT /admin/config"""

    def _update_and_verify(self, payload: dict, expected_code: int = 200):
        token = _admin_token()
        resp = client.put("/api/v1/admin/config",
                          json=payload,
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == expected_code, f"期望 {expected_code}，实际 {resp.status_code}: {resp.text}"
        if expected_code == 200:
            return resp.json()["data"]
        return resp.json()

    def test_update_scheduling_algorithm(self):
        """更新调度算法。"""
        data = self._update_and_verify({
            "schedulingAlgorithm": "batch_shortest",
        })
        assert data["schedulingAlgorithm"] == "batch_shortest"

    def test_update_base_service_fee(self):
        """更新基础服务费。"""
        data = self._update_and_verify({
            "baseServiceFee": 6.0,
        })
        assert data["baseServiceFee"] == 6.0

    def test_update_multiple_scalars(self):
        """同时更新多个标量字段。"""
        data = self._update_and_verify({
            "schedulingAlgorithm": "time_order",
            "baseServiceFee": 8.0,
        })
        assert data["schedulingAlgorithm"] == "time_order"
        assert data["baseServiceFee"] == 8.0

    def test_update_electricity_prices(self):
        """全量替换电价时段，字段名使用 start/end。"""
        data = self._update_and_verify({
            "electricityPrices": [
                {"periodName": "峰时", "start": "08:00", "end": "12:00", "pricePerKwh": 1.5},
                {"periodName": "谷时", "start": "12:00", "end": "08:00", "pricePerKwh": 0.3},
            ],
        })
        assert len(data["electricityPrices"]) == 2
        # 验证字段名
        p = data["electricityPrices"][0]
        assert p["periodName"] == "峰时"
        assert p["start"] == "08:00"
        assert p["end"] == "12:00"
        assert p["pricePerKwh"] == 1.5

    def test_update_service_fee_tiers(self):
        """全量替换服务费阶梯，含 tierName。"""
        data = self._update_and_verify({
            "serviceFeeTiers": [
                {"tierName": "基础", "minMinutes": 0, "maxMinutes": 30, "ratePerMinute": 0.1},
                {"tierName": "超时", "minMinutes": 30, "maxMinutes": None, "ratePerMinute": 0.2},
            ],
        })
        assert len(data["serviceFeeTiers"]) == 2
        t = data["serviceFeeTiers"][0]
        assert t["minMinutes"] == 0
        assert t["maxMinutes"] == 30
        assert t["ratePerMinute"] == 0.1

    def test_update_all_fields(self):
        """全字段更新。"""
        data = self._update_and_verify({
            "schedulingAlgorithm": "shortest_time_single",
            "baseServiceFee": 5.0,
            "electricityPrices": [
                {"periodName": "峰时", "start": "08:00", "end": "11:00", "pricePerKwh": 1.2},
                {"periodName": "平时", "start": "11:00", "end": "18:00", "pricePerKwh": 0.8},
                {"periodName": "峰时", "start": "18:00", "end": "21:00", "pricePerKwh": 1.2},
                {"periodName": "谷时", "start": "21:00", "end": "08:00", "pricePerKwh": 0.4},
            ],
            "serviceFeeTiers": [
                {"tierName": "基础阶梯", "minMinutes": 0, "maxMinutes": 60, "ratePerMinute": 0.15},
                {"tierName": "超时阶梯", "minMinutes": 60, "maxMinutes": None, "ratePerMinute": 0.20},
            ],
        })
        assert data["schedulingAlgorithm"] == "shortest_time_single"
        assert data["baseServiceFee"] == 5.0
        assert len(data["electricityPrices"]) == 4
        assert len(data["serviceFeeTiers"]) == 2

    def test_reject_time_conflict(self):
        """拒绝时间重叠的电价时段。"""
        self._update_and_verify({
            "electricityPrices": [
                {"periodName": "峰时", "start": "08:00", "end": "12:00", "pricePerKwh": 1.2},
                {"periodName": "平时", "start": "11:00", "end": "14:00", "pricePerKwh": 0.8},
            ],
        }, expected_code=400)

    def test_reject_cross_day_conflict(self):
        """拒绝跨天时段与正常时段重叠。"""
        self._update_and_verify({
            "electricityPrices": [
                {"periodName": "谷时", "start": "21:00", "end": "09:00", "pricePerKwh": 0.4},
                {"periodName": "峰时", "start": "08:00", "end": "11:00", "pricePerKwh": 1.2},
            ],
        }, expected_code=400)

    def test_allow_non_overlapping_adjacent(self):
        """允许紧邻（不重叠）的时段。"""
        data = self._update_and_verify({
            "electricityPrices": [
                {"periodName": "上午", "start": "08:00", "end": "12:00", "pricePerKwh": 1.0},
                {"periodName": "下午", "start": "12:00", "end": "18:00", "pricePerKwh": 0.8},
            ],
        })
        assert len(data["electricityPrices"]) == 2

    def test_reject_empty_prices(self):
        """电价时段列表不能为空。"""
        self._update_and_verify({
            "electricityPrices": [],
        }, expected_code=400)

    def test_reject_empty_tiers(self):
        """服务费阶梯列表不能为空。"""
        self._update_and_verify({
            "serviceFeeTiers": [],
        }, expected_code=400)

    def test_reject_invalid_price(self):
        """电价不能为负。"""
        self._update_and_verify({
            "electricityPrices": [
                {"periodName": "测试", "start": "00:00", "end": "01:00", "pricePerKwh": -0.5},
            ],
        }, expected_code=400)

    def test_reject_requires_admin(self):
        """普通用户不能更新配置。"""
        token = _user_token()
        resp = client.put("/api/v1/admin/config",
                          json={"baseServiceFee": 10.0},
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


class TestPersistence:
    """数据库持久化验证"""

    def test_db_prices_no_priority_column(self):
        """ElectricityPrice 表中不应有 priority 列。"""
        with DBSession(engine) as db:
            prices = db.exec(select(ElectricityPrice)).all()
            if prices:
                p = prices[0]
                # priority 不应是列属性
                assert not hasattr(p, "priority"), "priority 列应已移除"

    def test_update_persists_to_db(self):
        """PUT 的数据正确写入数据库。"""
        token = _admin_token()
        client.put("/api/v1/admin/config",
                    json={
                        "schedulingAlgorithm": "fault_recovery",
                        "baseServiceFee": 10.0,
                    },
                    headers={"Authorization": f"Bearer {token}"})

        with DBSession(engine) as db:
            algo = db.exec(
                select(GlobalConfig).where(GlobalConfig.config_key == "scheduling_algorithm")
            ).first()
            assert algo is not None
            assert algo.config_value == "fault_recovery"

            fee = db.exec(
                select(GlobalConfig).where(GlobalConfig.config_key == "base_service_fee")
            ).first()
            assert fee is not None
            assert fee.config_value == "10.0"
