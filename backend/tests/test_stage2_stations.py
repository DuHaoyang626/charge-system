"""
阶段 2 验证：充电桩模块 — 用户端查询 + 管理端增删改。
运行：pytest tests/test_stage2_stations.py -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

TEST_USER = {
    "licensePlate": "测试STN01",
    "userName": "充电桩测试车辆",
    "batteryCapacity": 60.0,
    "password": "test123456",
    "confirmPassword": "test123456",
    "protocolIds": [1, 3],
}


@pytest.fixture(scope="session")
def _setup_data():
    """确保测试用户存在（仅执行一次）。"""
    resp = client.post("/api/v1/auth/register", json=TEST_USER)
    if resp.status_code not in (200, 201):
        pass  # 用户可能已存在


@pytest.fixture
def user_token(_setup_data):
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "测试STN01",
        "password": "test123456",
    })
    return resp.json()["data"]["token"]


@pytest.fixture
def admin_token():
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN",
        "password": "admin123",
    })
    return resp.json()["data"]["token"]


class TestUserStations:
    def test_list_stations(self, user_token):
        resp = client.get("/api/v1/stations", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["stations"]) >= 2
        for s in data["stations"]:
            assert "name" in s
            assert "status" in s
            assert "supportedProtocols" in s

    def test_station_detail(self, user_token):
        resp = client.get("/api/v1/stations/1", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == 1
        assert "queueList" in data
        assert "chargingList" in data

    def test_station_not_found(self, user_token):
        resp = client.get("/api/v1/stations/999", headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 404


class TestAdminStations:
    def test_create_station(self, admin_token):
        resp = client.post("/api/v1/admin/stations",
            json={"name": "C区-03号桩", "queueCapacity": 5, "waitingCapacity": 3,
                  "chargingCapacity": 2, "protocolIds": [1, 3, 4]},
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code in (200, 201)

    def test_create_station_forbidden(self, user_token):
        resp = client.post("/api/v1/admin/stations",
            json={"name": "D区-04号桩", "queueCapacity": 5, "waitingCapacity": 3,
                  "chargingCapacity": 2, "protocolIds": [1]},
            headers={"Authorization": f"Bearer {user_token}"})
        assert resp.status_code == 403

    def test_start_stop_station(self, admin_token):
        # 停止
        resp = client.post("/api/v1/admin/stations/1/stop",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        # 启动
        resp = client.post("/api/v1/admin/stations/1/start",
            headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
