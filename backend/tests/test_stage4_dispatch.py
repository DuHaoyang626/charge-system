"""
阶段 4 验证：自动调度循环 — 排队→等待→充电→完成。
运行：pytest tests/test_stage4_dispatch.py -v
"""

import asyncio
from datetime import datetime, timedelta
import random

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.schedule_log import ScheduleLog
from model.session import ChargingSession
from model.station import Station
from scheduler.dispatch_loop import DispatchLoop

client = TestClient(app)


def _cleanup_stations():
    """清除其他测试可能留下的会话和桩计数，确保干净状态。"""
    with DBSession(engine) as db:
        # 清除排队的/等待中的非 charging 会话（保留后 stage5 创建的 charging 会话）
        stale = db.exec(
            select(ChargingSession).where(
                ChargingSession.status.in_(["queued", "waiting"])
            )
        ).all()
        for s in stale:
            db.delete(s)
        # 重置所有桩计数
        for station in db.exec(select(Station)).all():
            station.queue_count = 0
            station.waiting_count = 0
            station.charging_count = 0
            db.add(station)
        db.commit()


@pytest.mark.asyncio
async def test_dispatch_flow():
    _cleanup_stations()

    suffix = random.randint(10000, 99999)
    plate = f"调度测试{suffix}"
    r1 = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "调度测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 3],
    })
    token = r1.json()["data"]["token"]

    r2 = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 0.5, "protocolIds": [1, 3]},
        headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 201
    session_id = r2.json()["data"]["sessionId"]

    loop = DispatchLoop()

    # 阶段 1a：排队 → 等待（两区空，自动推进 queue→waiting 并标记 advance_ready）
    for i in range(8):
        await loop._tick()
        await asyncio.sleep(0.1)
        resp = client.get(f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        if data["status"] == "waiting":
            break

    assert data["status"] == "waiting", f"未能进入等待: {data['status']}"
    assert data["advanceReady"] is True, "应标记为充电就绪"
    print(f"  进入等待，advanceReady={data['advanceReady']}")

    # 阶段 1b：用户确认 → 进入充电
    resp = client.post(f"/api/v1/sessions/{session_id}/confirm-charging",
        json={"action": "confirm", "protocolId": 1},
        headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201), resp.json()
    data = resp.json()["data"]
    assert data["status"] == "charging", f"确认后应为 charging: {data['status']}"
    print(f"  进入充电，已充电量: {data.get('chargedEnergyKwh', 0)}")

    # 阶段 2：直接通过 DB 完成会话，验证调度循环检测完成
    with DBSession(engine) as db:
        s = db.get(ChargingSession, session_id)
        assert s is not None
        s.charged_energy_kwh = s.requested_energy_kwh
        # 将 last_tick 拨回 60 秒前，让增量能量越过目标
        loop._last_tick[s.id] = datetime.utcnow() - timedelta(seconds=60)
        db.add(s)
        db.commit()

    # 执行 tick，检测完成
    await loop._tick()
    await asyncio.sleep(0.1)

    resp = client.get(f"/api/v1/sessions/{session_id}",
        headers={"Authorization": f"Bearer {token}"})
    data = resp.json()["data"]

    assert data["status"] == "completed", f"预期完成，实际: {data['status']}"
    print(f"  充电完成，已充电量: {data['chargedEnergyKwh']}")

    # 验证账单
    assert data["bill"] is not None, "未生成账单"
    assert data["bill"]["totalFee"] > 0, f"账单金额不应为0: {data['bill']}"
    print(f"  账单总额: ¥{data['bill']['totalFee']}")

    # 验证调度日志
    with DBSession(engine) as db:
        logs = db.exec(
            select(ScheduleLog).where(ScheduleLog.session_id == session_id)
        ).all()
        assert len(logs) >= 2, f"调度日志不足: {len(logs)}"
        zones = [(l.from_zone, l.to_zone) for l in logs]
        print(f"  调度日志: {zones}")
        assert ("queue", "waiting") in zones
        assert ("waiting", "charging") in zones
