"""
阶段 4 验证：自动调度循环 — 排队→等待→充电→完成。
运行：pytest tests/test_stage4_dispatch.py -v
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session as DBSession, select

from core.database import engine
from main import app
from model.session import ChargingSession
from model.schedule_log import ScheduleLog
from scheduler.dispatch_loop import DispatchLoop

client = TestClient(app)


def _create_user_and_session(plate_suffix: str):
    """创建用户并发起充电请求，返回 (token, session_id)。"""
    plate = f"调度测试{plate_suffix}"
    r1 = client.post("/api/v1/auth/register", json={
        "licensePlate": plate, "userName": "调度测试", "batteryCapacity": 100,
        "password": "test123", "confirmPassword": "test123", "protocolIds": [1, 4],
    })
    assert r1.status_code in (200, 201)
    token = r1.json()["data"]["token"]

    r2 = client.post("/api/v1/sessions",
        json={"requestedEnergyKwh": 0.5, "protocolIds": [1, 4]},
        headers={"Authorization": f"Bearer {token}"})
    assert r2.status_code == 201
    session_id = r2.json()["data"]["sessionId"]
    return token, session_id


@pytest.mark.asyncio
async def test_dispatch_flow():
    """测试完整的调度流转：排队→等待→充电→完成。"""
    import random
    suffix = random.randint(10000, 99999)
    token, session_id = _create_user_and_session(suffix)

    loop = DispatchLoop()

    # ── 阶段 1：排队 → 等待 → 充电（不依赖时间） ──
    for i in range(6):
        await loop._tick()
        await asyncio.sleep(0.1)

        resp = client.get(f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        if data["status"] in ("charging", "completed"):
            break

    assert data["status"] in ("charging", "completed"), \
        f"未能进入充电状态: {data['status']}"
    print(f"  进入充电，已充电量: {data['chargedEnergyKwh']}")

    # ── 阶段 2：推进充电（模拟时间流逝） ──
    # 将 started_charging_at 拨回 60 秒前，模拟真实时间
    with DBSession(engine) as db:
        s = db.get(ChargingSession, session_id)
        if s and s.started_charging_at:
            s.started_charging_at = datetime.utcnow() - timedelta(seconds=60)
            db.add(s)
            db.commit()

    # 执行 tick，推进充电到完成
    for i in range(4):
        await loop._tick()
        await asyncio.sleep(0.1)
        resp = client.get(f"/api/v1/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"})
        data = resp.json()["data"]
        if data["status"] == "completed":
            break

    assert data["status"] == "completed", f"预期完成，实际: {data['status']}"
    print(f"  充电完成，已充电量: {data['chargedEnergyKwh']}")

    # ── 验证账单 ──
    assert data["bill"] is not None, "未生成账单"
    print(f"  账单总额: ¥{data['bill']['totalFee']}")

    # ── 验证调度日志 ──
    with DBSession(engine) as db:
        logs = db.exec(
            select(ScheduleLog).where(ScheduleLog.session_id == session_id)
        ).all()
        assert len(logs) >= 2, f"调度日志不足: {len(logs)}"
        zones = [(l.from_zone, l.to_zone) for l in logs]
        print(f"  调度日志: {zones}")
        assert ("queue", "waiting") in zones, "缺少 queue→waiting"
        assert ("waiting", "charging") in zones, "缺少 waiting→charging"
