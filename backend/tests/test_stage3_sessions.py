"""
阶段 3 验证：充电会话 — 发起、排队、换队、取消。
运行：pytest tests/test_stage3_sessions.py -v
"""

import random
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.fixture(scope="session")
def _setup():
    resp = client.post("/api/v1/auth/register", json={
        "licensePlate": "测试SES01", "userName": "会话测试",
        "batteryCapacity": 60.0, "password": "test123456",
        "confirmPassword": "test123456", "protocolIds": [1, 3],
    })
    return resp.status_code in (200, 201)


@pytest.fixture
def token(_setup):
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "测试SES01", "password": "test123456",
    })
    return resp.json()["data"]["token"]


def _make_user():
    """创建独立用户并返回 token。"""
    suffix = random.randint(1000, 9999)
    uniq = f"测试S3{suffix}"
    client.post("/api/v1/auth/register", json={
        "licensePlate": uniq, "userName": "t", "batteryCapacity": 60,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 3],
    })
    r = client.post("/api/v1/auth/login", json={"licensePlate": uniq, "password": "test123"})
    return r.json()["data"]["token"]


def _make_session(token):
    """创建会话并返回 sessionId。"""
    resp = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 60.0, "protocolIds": [1]},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201), f"创建会话失败: {resp.json()}"
    return resp.json()["data"]["sessionId"]


class TestCreateSession:
    def test_create_success(self, token):
        t = _make_user()
        resp = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 60.0, "protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["status"] == "queued"
        assert data["zone"] == "queue"
        assert data["queuePosition"] >= 1
        assert "station" in data

    def test_duplicate_session(self, token):
        t = _make_user()
        _make_session(t)  # 创建第 1 个
        resp = client.post("/api/v1/sessions",  # 第 2 个应失败
            json={"requestedEnergyKwh": 60.0, "protocolIds": [1]},
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code == 409

    def test_invalid_protocol(self, token):
        t = _make_user()
        resp = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 60.0, "protocolIds": [999]},
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code in (400, 409)


class TestGetSession:
    def test_get_detail(self, token):
        t = _make_user()
        sid = _make_session(t)
        resp = client.get(f"/api/v1/sessions/{sid}", headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == sid
        assert "currentFee" in data

    def test_get_other_users_session(self, token):
        t1 = _make_user()
        t2 = _make_user()
        sid = _make_session(t1)
        resp = client.get(f"/api/v1/sessions/{sid}",
            headers={"Authorization": f"Bearer {t2}"})
        assert resp.status_code == 403


class TestSwitchStation:
    def test_switch_options(self, token):
        t = _make_user()
        sid = _make_session(t)
        resp = client.get(f"/api/v1/sessions/{sid}/switch-options",
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "options" in data

    def test_switch_station(self, token):
        t = _make_user()
        sid = _make_session(t)
        resp = client.post(f"/api/v1/sessions/{sid}/switch-station",
            json={"targetStationId": 2},
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code in (200, 400)
        data = resp.json()["data"]
        assert "queuePosition" in data


class TestCancel:
    def test_cancel_queued(self, token):
        """排队区取消免费。"""
        t = _make_user()
        sid = _make_session(t)
        resp = client.post(f"/api/v1/sessions/{sid}/cancel",
            headers={"Authorization": f"Bearer {t}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "cancelled"
        assert data["bill"] is None
