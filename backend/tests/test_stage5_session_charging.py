"""
阶段 5 验证：充电阶段 — 确认、修改电量、修改协议、停止充电。
运行时跳过需要复杂调度的测试，直接测试端点核心逻辑。
运行：pytest tests/test_stage5_session_charging.py -v
"""

import random
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.session import ChargingSession
from model.station import Station

client = TestClient(app)


def _cleanup_station_counts():
    """清理所有残留会话并重置桩计数，避免跨测试污染。"""
    with DBSession(engine) as db:
        for s in db.exec(select(ChargingSession).where(
                ChargingSession.status.in_(["queued", "waiting", "charging"]))).all():
            db.delete(s)
        for st in db.exec(select(Station)).all():
            st.queue_count = 0
            st.waiting_count = 0
            st.charging_count = 0
            db.add(st)
        db.commit()


def make_user_and_session():
    """创建用户和排队会话，返回 (token, session_id)。"""
    _cleanup_station_counts()
    suffix = random.randint(10000, 99999)
    plate = f"S5T{suffix}"
    r1 = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "t", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 3],
    })
    token = r1.json()["data"]["token"]
    r2 = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 50.0, "protocolIds": [1, 3]},
        headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 201
    sid = r2.json()["data"]["sessionId"]
    return token, sid


def force_session_to_charging(token: str, sid: int):
    """直接通过 DB 将会话状态改为 charging（跳过调度循环）。"""
    from datetime import datetime
    from model.station import Station
    with DBSession(engine) as db:
        s = db.get(ChargingSession, sid)
        if s:
            # 同步更新桩计数：先减排队，再加等待
            station = db.get(Station, s.station_id)
            if station:
                station.queue_count = max(0, station.queue_count - 1)
                station.waiting_count = min(station.waiting_count + 1, station.waiting_capacity)
            s.status = "waiting"
            s.zone = "waiting"
            s.entered_waiting_at = datetime.utcnow()
            s.advance_ready = True
            db.add(s)
            if station:
                db.add(station)
            db.commit()
    # 通过 confirm API 进入充电
    resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
        json={"action": "confirm", "protocolId": 1},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201), f"force_session_to_charging 失败: {resp.json()}"


class TestModifyEnergy:
    def test_modify_energy_success(self):
        token, sid = make_user_and_session()
        force_session_to_charging(token, sid)
        resp = client.put(f"/api/v1/sessions/{sid}/energy",
            json={"requestedEnergyKwh": 60.0},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["requestedEnergyKwh"] == 60.0

    def test_modify_energy_too_low(self):
        token, sid = make_user_and_session()
        force_session_to_charging(token, sid)
        from datetime import datetime, timedelta
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                s.charged_energy_kwh = 10.0
                s.started_charging_at = datetime.utcnow() - timedelta(minutes=5)
                db.add(s)
                db.commit()
        resp = client.put(f"/api/v1/sessions/{sid}/energy",
            json={"requestedEnergyKwh": 5.0},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400


class TestProtocolOptions:
    def test_protocol_options(self):
        token, sid = make_user_and_session()
        resp = client.get(f"/api/v1/sessions/{sid}/protocol-options",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "options" in data

    def test_modify_protocol(self):
        token, sid = make_user_and_session()
        resp = client.put(f"/api/v1/sessions/{sid}/protocol",
            json={"protocolIds": [1, 3]},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200


class TestStopCharging:
    def test_stop_charging(self):
        token, sid = make_user_and_session()
        force_session_to_charging(token, sid)
        resp = client.post(f"/api/v1/sessions/{sid}/stop-charging",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "completed"
        assert "bill" in data
        assert data["bill"]["totalFee"] > 0
        # P1-04: 停止充电响应必须包含 electricityDetails
        assert "electricityDetails" in data["bill"]
        assert isinstance(data["bill"]["electricityDetails"], list)
        if data["bill"]["electricityDetails"]:
            item = data["bill"]["electricityDetails"][0]
            assert "period" in item
            assert "energy" in item
            assert "price" in item
            assert "fee" in item


class TestConfirmCharging:
    def test_confirm_charging_from_queue(self):
        """排队态 advance_ready → confirm → 进入等待区"""
        token, sid = make_user_and_session()
        from datetime import datetime
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                s.advance_ready = True
                db.add(s)
                db.commit()

        resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
            json={"action": "confirm", "protocolId": 1},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201), resp.json()
        data = resp.json()["data"]
        assert data["status"] == "waiting", f"预期 waiting，实际: {data['status']}"
        assert data["zone"] == "waiting"

    def test_reject_charging_from_queue(self):
        """排队态 advance_ready → reject → 免费取消"""
        token, sid = make_user_and_session()
        from datetime import datetime
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                s.advance_ready = True
                db.add(s)
                db.commit()

        resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
            json={"action": "reject"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201), resp.json()
        assert resp.json()["data"]["status"] == "cancelled"
        # 排队态免费取消，无账单
        assert resp.json()["data"].get("bill") is None

    def test_confirm_charging_from_waiting(self):
        """等待态 advance_ready → confirm → 开始充电"""
        token, sid = make_user_and_session()
        from datetime import datetime
        from model.station import Station
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                # 同步更新桩计数：减排队、加等待
                station = db.get(Station, s.station_id)
                if station:
                    station.queue_count = max(0, station.queue_count - 1)
                    station.waiting_count = min(station.waiting_count + 1, station.waiting_capacity)
                    db.add(station)
                s.status = "waiting"
                s.zone = "waiting"
                s.entered_waiting_at = datetime.utcnow()
                s.advance_ready = True
                db.add(s)
                db.commit()

        resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
            json={"action": "confirm", "protocolId": 1},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201), resp.json()
        assert resp.json()["data"]["status"] == "charging"

    def test_reject_charging_from_waiting(self):
        """等待态 advance_ready → reject → 收基础服务费取消"""
        token, sid = make_user_and_session()
        from datetime import datetime
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                s.status = "waiting"
                s.zone = "waiting"
                s.entered_waiting_at = datetime.utcnow()
                s.advance_ready = True
                db.add(s)
                db.commit()

        resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
            json={"action": "reject"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code in (200, 201)
        assert resp.json()["data"]["status"] == "cancelled"
        assert resp.json()["data"]["bill"] is not None

    def test_confirm_without_advance_ready(self):
        """未标记 advance_ready 时拒绝确认"""
        token, sid = make_user_and_session()
        from datetime import datetime
        with DBSession(engine) as db:
            s = db.get(ChargingSession, sid)
            if s:
                s.status = "waiting"
                s.zone = "waiting"
                s.entered_waiting_at = datetime.utcnow()
                s.advance_ready = False
                db.add(s)
                db.commit()

        resp = client.post(f"/api/v1/sessions/{sid}/confirm-charging",
            json={"action": "confirm", "protocolId": 1},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400, resp.json()
        assert "暂未调度" in resp.json()["message"]
