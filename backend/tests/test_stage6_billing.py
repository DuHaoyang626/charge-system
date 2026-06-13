"""
阶段 6 验证：账单与支付 — 账单生成、详情、列表、支付、重复支付。
运行：pytest tests/test_stage6_billing.py -v
"""

import asyncio
from datetime import datetime, timedelta
import random

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.session import ChargingSession
from model.station import Station
from scheduler.dispatch_loop import DispatchLoop
from service.billing.service import generate_bill

client = TestClient(app)


def _cleanup():
    """清除其他测试可能留下的会话和桩计数。"""
    with DBSession(engine) as db:
        for s in db.exec(select(ChargingSession).where(
                ChargingSession.status.in_(["queued", "waiting"]))).all():
            db.delete(s)
        for station in db.exec(select(Station)).all():
            station.queue_count = 0
            station.waiting_count = 0
            station.charging_count = 0
            db.add(station)
        db.commit()


async def _create_completed_session() -> tuple[str, int]:
    """创建并完成一个充电会话，返回 (token, session_id)。"""
    suffix = random.randint(10000, 99999)
    plate = f"账单测试{suffix}"
    r1 = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "账单测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 4],
    })
    token = r1.json()["data"]["token"]

    r2 = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 0.5, "protocolIds": [1, 4]},
        headers={"Authorization": f"Bearer {token}"})
    sid = r2.json()["data"]["sessionId"]

    loop = DispatchLoop()

    # 等待调度到 waiting 且 advance_ready = True
    for _ in range(8):
        await loop._tick()
        resp = client.get(f"/api/v1/sessions/{sid}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        if data.get("advanceReady") is True and data["status"] == "waiting":
            break

    # 确认充电
    client.post(f"/api/v1/sessions/{sid}/confirm-charging",
        json={"action": "confirm", "protocolId": 4},
        headers={"Authorization": f"Bearer {token}"})

    # 直接通过 DB 完成会话（设置合理的充电时长）
    with DBSession(engine) as db:
        s = db.get(ChargingSession, sid)
        if s:
            now = datetime.utcnow()
            s.started_charging_at = now - timedelta(minutes=30)
            s.completed_at = now
            s.charged_energy_kwh = s.requested_energy_kwh
            s.status = "completed"
            s.zone = None
            db.add(s)
            db.commit()
            loop._last_tick.pop(s.id, None)

    # 确保 dispatch loop 触发完成事件并生成账单
    await loop._tick()

    # 确保账单已生成
    generate_bill(sid)
    return token, sid


@pytest.mark.asyncio
class TestBillingList:
    async def test_bill_list(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["list"]) > 0
        assert data["total"] > 0
        assert data["page"] == 1
        item = data["list"][0]
        assert "billId" in item
        assert "sessionId" in item
        assert "station" in item
        assert item["totalFee"] > 0
        assert item["paymentStatus"] == "unpaid"

    async def test_bill_list_pagination(self):
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills?page=1&pageSize=5",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_bill_list_filter_paid(self):
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills?paymentStatus=paid",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert len(resp.json()["data"]["list"]) == 0


@pytest.mark.asyncio
class TestBillingDetail:
    async def test_bill_detail(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.get(f"/api/v1/bills/{bill_id}",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["totalFee"] > 0
        assert data["electricityFee"] >= 0
        assert data["totalServiceFee"] > 0
        assert data["baseServiceFee"] > 0
        assert data["chargingDuration"] is not None
        assert len(data["electricityDetails"]) > 0
        assert len(data["serviceFeeTiers"]) > 0

    async def test_bill_detail_forbidden(self):
        _cleanup()
        token1, _ = await _create_completed_session()
        suffix = random.randint(10000, 99999)
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": f"其他用户{suffix}", "userName": "其他", "batteryCapacity": 60,
            "password": "test123", "confirmPassword": "test123", "protocolIds": [1],
        })
        token2 = r.json()["data"]["token"]

        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token1}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.get(f"/api/v1/bills/{bill_id}",
            headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403

    async def test_bill_detail_not_found(self):
        suffix = random.randint(10000, 99999)
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": f"无账单用户{suffix}", "userName": "无账单", "batteryCapacity": 60,
            "password": "test123", "confirmPassword": "test123", "protocolIds": [1],
        })
        token = r.json()["data"]["token"]

        resp = client.get("/api/v1/bills/99999",
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestBillingPayment:
    async def test_payment_success(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "wechat"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.json()
        data = resp.json()["data"]
        assert data["paymentStatus"] == "paid"
        assert "transactionId" in data
        assert data["totalFee"] > 0

    async def test_duplicate_payment(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "wechat"},
            headers={"Authorization": f"Bearer {token}"})

        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "alipay"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400
        assert "已支付" in resp.json()["message"]

    async def test_pay_others_bill(self):
        _cleanup()
        token1, _ = await _create_completed_session()
        suffix = random.randint(10000, 99999)
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": f"支付测试{suffix}", "userName": "支付测试", "batteryCapacity": 60,
            "password": "test123", "confirmPassword": "test123", "protocolIds": [1],
        })
        token2 = r.json()["data"]["token"]

        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token1}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={"paymentMethod": "wechat"},
            headers={"Authorization": f"Bearer {token2}"})
        assert resp.status_code == 403

    async def test_pay_no_method(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.post(f"/api/v1/bills/{bill_id}/pay",
            json={},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 400

    async def test_pay_not_found(self):
        suffix = random.randint(10000, 99999)
        r = client.post("/api/v1/auth/register", json={
            "licensePlate": f"支付不存在{suffix}", "userName": "支付不存在", "batteryCapacity": 60,
            "password": "test123", "confirmPassword": "test123", "protocolIds": [1],
        })
        token = r.json()["data"]["token"]

        resp = client.post("/api/v1/bills/99999/pay",
            json={"paymentMethod": "wechat"},
            headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 404


@pytest.mark.asyncio
class TestBillingTotal:
    async def test_total_fee_consistency(self):
        _cleanup()
        token, _ = await _create_completed_session()
        resp = client.get("/api/v1/bills",
            headers={"Authorization": f"Bearer {token}"})
        bill_id = resp.json()["data"]["list"][0]["billId"]

        resp = client.get(f"/api/v1/bills/{bill_id}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        expected = round(data["electricityFee"] + data["totalServiceFee"], 2)
        assert data["totalFee"] == expected, (
            f"电费 {data['electricityFee']} + 服务费 {data['totalServiceFee']}"
            f" = {expected} ≠ 总费用 {data['totalFee']}"
        )
