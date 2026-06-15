"""
P0-05/P0-06/P0-07/P2-01 验证：管理端账单、紧急停止、队列移动、报表 — 严格遵循 API 接口说明。

测试覆盖：
  - GET /admin/bills 返回嵌套 user/station 结构
  - POST /admin/stations/:id/emergency-stop 响应格式
  - PUT /admin/queues/move 请求含 targetZone
  - GET /admin/reports/* 三个报表接口参数和响应结构

运行：pytest tests/test_admin_misc.py -v
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.bill import Bill
from model.session import ChargingSession
from model.station import Station

client = TestClient(app)


def _admin_token() -> str:
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "ADMIN", "password": "admin123",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


def _user_token() -> str:
    client.post("/api/v1/auth/register", json={
        "licensePlate": "测试ADM01", "userName": "管理端测试车辆",
        "batteryCapacity": 60.0, "password": "test123456",
        "confirmPassword": "test123456", "protocolIds": [1, 3],
    })
    resp = client.post("/api/v1/auth/login", json={
        "licensePlate": "测试ADM01", "password": "test123456",
    })
    assert resp.status_code == 200
    return resp.json()["data"]["token"]


@pytest.fixture(scope="module")
def admin_headers():
    return {"Authorization": f"Bearer {_admin_token()}"}


# ══════════════════════════════════════════════════════════════
# P0-05: GET /admin/bills
# ══════════════════════════════════════════════════════════════


class TestAdminBills:
    def test_list_structure(self, admin_headers):
        """响应结构严格遵循 API 接口说明。"""
        resp = client.get("/api/v1/admin/bills", headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "list" in data
        assert "page" in data
        assert "pageSize" in data
        assert "total" in data

        if data["list"]:
            b = data["list"][0]
            # 核心字段
            assert "billId" in b
            assert "sessionId" in b
            assert "user" in b
            assert isinstance(b["user"], dict)
            assert "id" in b["user"]
            assert "licensePlate" in b["user"]
            assert "station" in b
            assert isinstance(b["station"], dict)
            assert "id" in b["station"]
            assert "name" in b["station"]
            assert "chargedEnergyKwh" in b
            assert "totalFee" in b
            assert "paymentStatus" in b
            assert "createdAt" in b

            # 平铺字段不应存在
            assert "userId" not in b
            assert "licensePlate" not in b
            assert "stationName" not in b
            assert "electricityFee" not in b
            assert "serviceFee" not in b
            assert "totalEnergyKwh" not in b

    def test_list_requires_admin(self):
        """普通用户无权访问。"""
        token = _user_token()
        resp = client.get("/api/v1/admin/bills",
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_list_pagination(self, admin_headers):
        """分页参数正常。"""
        resp = client.get("/api/v1/admin/bills", params={
            "page": 1, "pageSize": 5,
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["page"] == 1
        assert data["pageSize"] == 5


# ══════════════════════════════════════════════════════════════
# P0-06: POST /admin/stations/:id/emergency-stop
# ══════════════════════════════════════════════════════════════


class TestEmergencyStop:
    def test_emergency_stop_structure(self, admin_headers):
        """响应结构严格遵循 API 接口说明。"""
        # 先找第一个 running 桩
        with DBSession(engine) as db:
            station = db.exec(
                select(Station).where(Station.status == "running")
            ).first()
            if not station:
                pytest.skip("无 running 充电桩")
            sid = station.id

        resp = client.post(f"/api/v1/admin/stations/{sid}/emergency-stop",
                           json={"algorithm": "shortest_time_single"},
                           headers=admin_headers)
        # 允许 200 或 400（无车辆时可能直接成功或返回提示）
        assert resp.status_code in (200, 400)

        if resp.status_code == 200:
            data = resp.json()["data"]
            # 文档要求的字段
            assert "message" in data
            assert "status" in data
            assert data["status"] == "stopped", f"期望 stopped，实际 {data['status']}"
            assert "algorithm" in data
            assert "redistributedSessions" in data
            assert isinstance(data["redistributedSessions"], list)

            if data["redistributedSessions"]:
                rs = data["redistributedSessions"][0]
                assert "sessionId" in rs
                assert "fromStation" in rs
                assert "toStation" in rs
                assert "newPosition" in rs

            # chargingSessions 必须存在
            assert "chargingSessions" in data
            assert isinstance(data["chargingSessions"], list)

            # failedSessions 不应存在
            assert "failedSessions" not in data, "failedSessions 应移除"

        # 恢复桩状态以免影响后续测试
        with DBSession(engine) as db:
            st = db.get(Station, sid)
            if st:
                st.status = "running"
                st.queue_count = 0
                st.waiting_count = 0
                st.charging_count = 0
                db.add(st)
                db.commit()

    def test_emergency_stop_requires_admin(self):
        """普通用户无权调用。"""
        token = _user_token()
        resp = client.post("/api/v1/admin/stations/1/emergency-stop",
                           json={"algorithm": "shortest_time_single"},
                           headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_emergency_stop_not_found(self, admin_headers):
        """不存在的桩返回 404。"""
        resp = client.post("/api/v1/admin/stations/99999/emergency-stop",
                           json={"algorithm": "shortest_time_single"},
                           headers=admin_headers)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════
# P0-07: PUT /admin/queues/move
# ══════════════════════════════════════════════════════════════


class TestQueueMove:
    def test_move_requires_target_zone(self, admin_headers):
        """请求必须含 targetZone。"""
        # 不带 targetZone → 422 校验失败
        resp = client.put("/api/v1/admin/queues/move",
                          json={
                              "sessionId": 1,
                              "targetStationId": 2,
                              "targetPosition": 1,
                          },
                          headers=admin_headers)
        # FastAPI/Pydantic 校验失败返回 422
        assert resp.status_code == 422, f"期望 422，实际 {resp.status_code}: {resp.text}"

    def test_move_success(self, admin_headers):
        """带 targetZone 的正常请求。"""
        # 创建测试用户 + 会话
        import random
        suffix = random.randint(10000, 99999)
        plate = f"移动测试{suffix}"
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": plate, "userName": "移动测试车",
            "batteryCapacity": 60.0, "password": "test123",
            "confirmPassword": "test123", "protocolIds": [1, 3],
        })
        token = r.json()["data"]["token"]
        r2 = client.post("/api/v1/sessions",
            json={"requestedEnergyKwh": 30.0, "protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 201
        sid = r2.json()["data"]["sessionId"]

        with DBSession(engine) as db:
            other = db.exec(
                select(Station).where(
                    Station.status == "running",
                )
            ).first()
            if not other:
                pytest.skip("无 running 充电桩")
            target_id = other.id

        resp = client.put("/api/v1/admin/queues/move",
                          json={
                              "sessionId": sid,
                              "targetStationId": target_id,
                              "targetZone": "queue",
                              "targetPosition": -1,
                          },
                          headers=admin_headers)
        assert resp.status_code == 200, f"请求失败: {resp.text}"
        data = resp.json()["data"]
        assert data["sessionId"] == sid
        assert data["toStationId"] == target_id
        assert data["zone"] == "queue"
        assert "newPosition" in data

        # 清理：取消该会话，释放排队槽位
        client.post(f"/api/v1/sessions/{sid}/cancel",
                    headers={"Authorization": f"Bearer {token}"})

    def test_move_requires_admin(self):
        """普通用户无权调用。"""
        token = _user_token()
        resp = client.put("/api/v1/admin/queues/move",
                          json={
                              "sessionId": 1, "targetStationId": 2,
                              "targetZone": "queue", "targetPosition": -1,
                          },
                          headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403


# ══════════════════════════════════════════════════════════════
# P2-01: 报表接口
# ══════════════════════════════════════════════════════════════


class TestReports:
    """三个报表接口 — 参数和响应结构严格遵循 API 接口说明。"""

    def test_charging_volume_structure(self, admin_headers):
        """充电量统计响应结构。"""
        resp = client.get("/api/v1/admin/reports/charging-volume", params={
            "startDate": "2026-01-01", "endDate": "2026-06-15", "granularity": "month",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "totalEnergyKwh" in data
        assert isinstance(data["totalEnergyKwh"], (int, float))
        assert "totalSessions" in data
        assert isinstance(data["totalSessions"], int)
        assert "dataPoints" in data
        assert isinstance(data["dataPoints"], list)

        if data["dataPoints"]:
            dp = data["dataPoints"][0]
            assert "period" in dp
            assert "energyKwh" in dp
            assert "sessions" in dp

    def test_charging_volume_missing_params(self, admin_headers):
        """缺少必填参数返回 400。"""
        resp = client.get("/api/v1/admin/reports/charging-volume",
                          headers=admin_headers)
        assert resp.status_code == 400

    def test_charging_volume_invalid_granularity(self, admin_headers):
        """不支持的粒度返回 400。"""
        resp = client.get("/api/v1/admin/reports/charging-volume", params={
            "startDate": "2026-01-01", "endDate": "2026-06-15", "granularity": "year",
        }, headers=admin_headers)
        assert resp.status_code == 400

    def test_revenue_structure(self, admin_headers):
        """收入统计响应结构。"""
        resp = client.get("/api/v1/admin/reports/revenue", params={
            "startDate": "2026-01-01", "endDate": "2026-06-15", "granularity": "month",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "totalRevenue" in data
        assert "electricityRevenue" in data
        assert "serviceRevenue" in data
        assert "dataPoints" in data
        assert isinstance(data["dataPoints"], list)

        if data["dataPoints"]:
            dp = data["dataPoints"][0]
            assert "period" in dp
            assert "revenue" in dp
            assert "electricity" in dp
            assert "service" in dp

    def test_revenue_missing_params(self, admin_headers):
        """缺少必填参数返回 400。"""
        resp = client.get("/api/v1/admin/reports/revenue",
                          headers=admin_headers)
        assert resp.status_code == 400

    def test_utilization_structure(self, admin_headers):
        """充电桩利用率响应结构。"""
        resp = client.get("/api/v1/admin/reports/utilization", params={
            "startDate": "2026-01-01", "endDate": "2026-06-15",
        }, headers=admin_headers)
        assert resp.status_code == 200
        data = resp.json()["data"]

        assert "overallUtilization" in data
        assert isinstance(data["overallUtilization"], (int, float))
        assert "stations" in data
        assert isinstance(data["stations"], list)

        if data["stations"]:
            s = data["stations"][0]
            assert "stationId" in s
            assert "stationName" in s
            assert "utilization" in s
            assert "totalChargingHours" in s
            assert "totalAvailableHours" in s

    def test_utilization_missing_params(self, admin_headers):
        """缺少必填参数返回 400。"""
        resp = client.get("/api/v1/admin/reports/utilization",
                          headers=admin_headers)
        assert resp.status_code == 400

    def test_reports_require_admin(self):
        """普通用户无权访问报表。"""
        token = _user_token()
        for path in ["/api/v1/admin/reports/charging-volume",
                     "/api/v1/admin/reports/revenue",
                     "/api/v1/admin/reports/utilization"]:
            resp = client.get(path, params={
                "startDate": "2026-01-01", "endDate": "2026-06-15",
            }, headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 403, f"{path} 应返回 403"