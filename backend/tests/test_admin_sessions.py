"""
P0-03/P0-04 验证：管理端会话管理 — 严格遵循 API 接口说明。

测试覆盖：
  - GET /admin/sessions 返回结构符合 API 文档（sessionId、嵌套 user/station、progress）
  - GET /admin/sessions/:id 返回结构符合 API 文档（user 包裹 + 同 GET /sessions/:id）
  - 权限校验（普通用户拒绝）
  - 分页和筛选

运行：pytest tests/test_admin_sessions.py -v
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def _admin_token() -> str:
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN", "password": "admin123",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def _user_token() -> str:
    """注册 + 登录普通用户（幂等）。"""
    client.post("/api/v1/auth/register", json={
        "licensePlate": "测试SESS01", "userName": "会话测试车辆",
        "batteryCapacity": 60.0, "password": "test123456",
        "confirmPassword": "test123456", "protocolIds": [1],
    })
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "测试SESS01", "password": "test123456",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_admin_token()}"}


@pytest.fixture(scope="module")
def user_headers():
    return {"Authorization": f"Bearer {_user_token()}"}


class TestAdminSessionList:
    """GET /admin/sessions"""

    def test_list_structure(self, admin_headers):
        """响应结构严格遵循 API 接口说明。"""
        resp = client.get("/api/v1/admin/sessions", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "list" in data
        assert "page" in data
        assert "pageSize" in data
        assert "total" in data
        assert isinstance(data["list"], list)

        if data["list"]:
            s = data["list"][0]
            # 字段名：sessionId（不是 id）
            assert "sessionId" in s
            assert "id" not in s

            # user 嵌套对象
            assert "user" in s
            assert isinstance(s["user"], dict)
            assert "id" in s["user"]
            assert "licensePlate" in s["user"]

            # station 嵌套对象
            assert "station" in s
            assert isinstance(s["station"], dict)
            assert "id" in s["station"]
            assert "name" in s["station"]

            # 核心字段
            assert "status" in s
            assert "requestedEnergyKwh" in s
            assert "chargedEnergyKwh" in s
            assert "progress" in s
            assert "createdAt" in s

            # 不应包含平铺字段
            assert "userId" not in s
            assert "licensePlate" not in s
            assert "stationId" not in s
            assert "stationName" not in s
            assert "zone" not in s
            assert "advanceReady" not in s

    def test_list_pagination(self, admin_headers):
        """分页参数正常。"""
        resp = client.get("/api/v1/admin/sessions", params={
            "page": 1, "pageSize": 5,
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["pageSize"] == 5
        assert len(data["list"]) <= 5

    def test_list_filter_status(self, admin_headers):
        """按状态筛选。"""
        resp = client.get("/api/v1/admin/sessions", params={
            "status": "queued",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        for s in data["list"]:
            assert s["status"] == "queued"

    def test_list_requires_admin(self, user_headers):
        """普通用户无权访问。"""
        resp = client.get("/api/v1/admin/sessions", headers=user_headers)
        assert resp.status_code == 403

    def test_list_no_auth(self):
        """未认证返回 401。"""
        resp = client.get("/api/v1/admin/sessions")
        assert resp.status_code == 401


class TestAdminSessionDetail:
    """GET /admin/sessions/:id"""

    def _create_test_session(self, admin_headers) -> int:
        """创建一个测试会话并返回 sessionId。"""
        # 注册一个测试用户
        import random
        suffix = random.randint(10000, 99999)
        plate = f"管理端测试{suffix}"
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": plate, "userName": "测试车",
            "batteryCapacity": 60.0, "password": "test123",
            "confirmPassword": "test123", "protocolIds": [1, 3],
        })
        token = r.json()["data"]["token"]

        r2 = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 30.0, "protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 201
        return r2.json()["data"]["sessionId"]

    def test_detail_structure(self, admin_headers):
        """响应结构严格遵循 API 接口说明。"""
        session_id = self._create_test_session(admin_headers)

        resp = client.get(f"/api/v1/admin/sessions/{session_id}",
                          headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        # user 嵌套对象
        assert "user" in data
        assert isinstance(data["user"], dict)
        assert "id" in data["user"]
        assert "licensePlate" in data["user"]

        # 同 GET /sessions/:id 的所有字段
        assert "id" in data
        assert "status" in data
        assert "zone" in data
        assert "station" in data
        assert isinstance(data["station"], dict)
        assert "id" in data["station"]
        assert "name" in data["station"]
        assert "requestedEnergyKwh" in data
        assert "chargedEnergyKwh" in data
        assert "progress" in data
        assert "queuePosition" in data
        assert "supportedProtocols" in data
        assert isinstance(data["supportedProtocols"], list)
        assert "enteredQueueAt" in data
        assert "currentFee" in data
        assert isinstance(data["currentFee"], dict)

        # 平铺字段不应存在
        assert "userId" not in data
        assert "userName" not in data
        assert "stationId" not in data
        assert "stationName" not in data

    def test_detail_not_found(self, admin_headers):
        """不存在的会话返回 404。"""
        resp = client.get("/api/v1/admin/sessions/99999",
                          headers=admin_headers)
        assert resp.status_code == 404

    def test_detail_requires_admin(self, user_headers):
        """普通用户无权访问。"""
        resp = client.get("/api/v1/admin/sessions/1",
                          headers=user_headers)
        assert resp.status_code == 403
