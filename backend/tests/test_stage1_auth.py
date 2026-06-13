"""
阶段 1 验证：认证模块 — 注册、登录、获取用户信息。
运行：pytest tests/test_stage1_auth.py -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

REGISTER_DATA = {
    "licensePlate": "粤B12345",
    "userName": "测试车辆",
    "batteryCapacity": 60.0,
    "password": "test123456",
    "confirmPassword": "test123456",
    "protocolIds": [1, 3],
}


class TestRegister:
    def test_register_success(self):
        resp = client.post("/api/v1/auth/register", json=REGISTER_DATA)
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert "token" in data
        assert data["licensePlate"] == "粤B12345"
        assert data["userName"] == "测试车辆"

    def test_register_duplicate_plate(self):
        resp = client.post("/api/v1/auth/register", json=REGISTER_DATA)
        assert resp.status_code == 400
        assert "已注册" in resp.json()["message"]

    def test_register_password_mismatch(self):
        data = {**REGISTER_DATA, "licensePlate": "粤C67890", "confirmPassword": "different"}
        resp = client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400

    def test_register_invalid_protocol(self):
        data = {**REGISTER_DATA, "licensePlate": "粤D67890", "protocolIds": [999]}
        resp = client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "test123456",
        })
        assert resp.status_code == 200
        assert "token" in resp.json()["data"]

    def test_login_wrong_password(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "wrongpassword",
        })
        assert resp.status_code == 400

    def test_login_nonexistent(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "京NONEXIST",
            "password": "test123456",
        })
        assert resp.status_code == 400


class TestUserMe:
    def _login(self):
        resp = client.post("/api/v1/auth/login", json={
            "licensePlate": "粤B12345",
            "password": "test123456",
        })
        return resp.json()["data"]["token"]

    def test_get_user_me_success(self):
        token = self._login()
        resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["licensePlate"] == "粤B12345"
        assert "batteryCapacity" in data
        assert "protocols" in data

    def test_get_user_me_no_token(self):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401

    def test_get_user_me_invalid_token(self):
        resp = client.get("/api/v1/users/me", headers={"Authorization": "Bearer invalid"})
        assert resp.status_code == 401
