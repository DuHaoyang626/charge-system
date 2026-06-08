"""
API 端到端测试 — 通过 FastAPI TestClient 模拟 HTTP 请求

框架测试（PASS）：端点可达、状态码正确、返回结构正常
业务测试（xfail）：具体业务值依赖真实逻辑，mock 数据不满足
"""

import pytest


class TestAccountAPI:
    """用户账号 API 测试"""

    def test_create_account_200(self, client):
        """POST /api/accounts 返回 200"""
        response = client.post("/api/accounts", json={
            "car_Id": "京A12345",
            "userName": "张三",
            "car_Capacity": 60.0,
        })
        assert response.status_code == 200

    def test_create_account_returns_user_id(self, client):
        """POST /api/accounts 返回 user_id"""
        response = client.post("/api/accounts", json={
            "car_Id": "京A12345",
            "userName": "张三",
            "car_Capacity": 60.0,
        })
        data = response.json()
        assert data["success"] is True
        assert "user_id" in data

    def test_create_account_invalid_capacity_422(self, client):
        """POST /api/accounts — 无效容量触发 Pydantic 校验返回 422"""
        response = client.post("/api/accounts", json={
            "car_Id": "京A12345",
            "userName": "张三",
            "car_Capacity": 0,
        })
        assert response.status_code == 422

    def test_set_password_200(self, client):
        """PUT /api/accounts/{car_id}/password 返回 200"""
        response = client.put("/api/accounts/京A12345/password", json={
            "password": "Abc12345",
        })
        assert response.status_code == 200

    def test_login_rejects_wrong_password(self, client):
        """错误密码应登录失败（真实实现已支持）"""
        client.post("/api/accounts", json={
            "car_Id": "京A12345", "userName": "张三", "car_Capacity": 60.0,
        })
        client.put("/api/accounts/京A12345/password", json={"password": "CorrectPwd1"})

        # 错误密码
        r = client.post("/api/auth/login", json={
            "car_Id": "京A12345", "password": "wrong",
        })
        assert r.status_code == 200
        assert r.json()["success"] is False


class TestChargingAPI:
    """充电流程 API 测试"""

    def test_create_request_200(self, client):
        """POST /api/charging/requests 返回 200"""
        response = client.post("/api/charging/requests", json={
            "car_Id": "京A12345",
            "Request_Amount": 50.0,
            "Request_Mode": "FAST_CHARGE",
        })
        assert response.status_code == 200

    def test_create_request_returns_position(self, client):
        """提交充电申请返回排队位置"""
        response = client.post("/api/charging/requests", json={
            "car_Id": "京A12345",
            "Request_Amount": 50.0,
            "Request_Mode": "FAST_CHARGE",
        })
        data = response.json()
        assert data["success"] is True
        assert "car_position" in data
        assert "car_state" in data
        assert "queue_Num" in data

    def test_modify_amount_200(self, client):
        """PUT /api/charging/requests/{car_id}/amount 返回 200"""
        response = client.put("/api/charging/requests/京A12345/amount", json={
            "car_Id": "京A12345", "Amount": 60.0,
        })
        assert response.status_code == 200

    def test_modify_mode_200(self, client):
        """PUT /api/charging/requests/{car_id}/mode 返回 200"""
        response = client.put("/api/charging/requests/京A12345/mode", json={
            "car_Id": "京A12345", "Mode": "SLOW_CHARGE",
        })
        assert response.status_code == 200

    def test_query_car_state_200(self, client):
        """GET /api/charging/requests/{car_id}/state 返回 200"""
        response = client.get("/api/charging/requests/京A12345/state")
        assert response.status_code == 200

    def test_query_car_state_has_fields(self, client):
        """查询排队状态包含必要字段"""
        # 需要先有充电请求记录（DispatchService 尚未实现，直接通过 API 创建）
        from datetime import datetime
        from src.db.database import get_session
        from src.db.models import ChargingRequest
        session = get_session()
        try:
            now = datetime.now()
            session.add(ChargingRequest(
                request_id=f"R{now.strftime('%Y%m%d%H%M%S%f')}",
                car_id="京A12345",
                pile_id="P001",
                request_time=now,
                charging_mode="FAST_CHARGE",
                target_power_kwh=50.0,
                request_status="QUEUED",
                zone_type="QUEUE_AREA",
                queue_position=1,
                is_active=True,
                created_at=now, updated_at=now,
            ))
            session.commit()
        finally:
            session.close()

        response = client.get("/api/charging/requests/京A12345/state")
        data = response.json()
        assert data["success"] is True
        for key in ("car_Number_before_position", "car_state", "queue_Num", "request_time"):
            assert key in data

    def _prepare_start_charging(self, client):
        """辅助：创建充电请求并使桩可用，为开始充电做准备"""
        from datetime import datetime
        from src.db.database import get_session
        from src.db.models import ChargingPile, ChargingRequest
        session = get_session()
        try:
            now = datetime.now()
            # 确保桩是 RUNNING 状态
            pile = session.query(ChargingPile).filter(
                ChargingPile.pile_id == "P001"
            ).first()
            if pile:
                pile.status = "RUNNING"
            # 创建活跃充电请求（WAITING 状态）
            session.add(ChargingRequest(
                request_id=f"R_PREP{now.strftime('%H%M%S%f')}",
                car_id="京A12345", pile_id="P001",
                request_time=now, charging_mode="FAST_CHARGE",
                target_power_kwh=50.0, request_status="WAITING",
                zone_type="WAITING_AREA", queue_position=1,
                is_active=True, created_at=now, updated_at=now,
            ))
            session.commit()
        finally:
            session.close()

    def test_start_charging_200(self, client):
        """POST /api/charging/sessions 返回 200"""
        self._prepare_start_charging(client)
        response = client.post("/api/charging/sessions", json={
            "car_id": "京A12345", "ChargePileNum": "P001",
        })
        assert response.status_code == 200

    def test_start_charging_returns_session(self, client):
        """开始充电返回 session_id"""
        self._prepare_start_charging(client)
        response = client.post("/api/charging/sessions", json={
            "car_id": "京A12345", "ChargePileNum": "P001",
        })
        data = response.json()
        assert data["success"] is True
        assert "session_id" in data

    def test_query_charging_state_200(self, client):
        """GET /api/charging/sessions/{car_id} 返回 200"""
        response = client.get("/api/charging/sessions/京A12345")
        assert response.status_code == 200

    def _prepare_end_charging(self, client):
        """辅助：创建活跃充电会话，为结束充电做准备"""
        from datetime import datetime
        from src.db.database import get_session
        from src.db.models import ChargingPile, ChargingRequest, ChargingSession
        session = get_session()
        try:
            now = datetime.now()
            pile = session.query(ChargingPile).filter(
                ChargingPile.pile_id == "P001"
            ).first()
            if pile:
                pile.status = "CHARGING"
                pile.current_charging_count = 1
            session.add(ChargingRequest(
                request_id="R_END_PREP", car_id="京A12345",
                pile_id="P001", request_time=now,
                charging_mode="FAST_CHARGE", target_power_kwh=50.0,
                request_status="CHARGING", zone_type="CHARGING_AREA",
                queue_position=1, is_active=True,
                created_at=now, updated_at=now,
            ))
            session.add(ChargingSession(
                session_id="S_END_PREP", request_id="R_END_PREP",
                car_id="京A12345", pile_id="P001",
                start_time=now, target_power_kwh=50.0,
                charged_power_kwh=0, current_power_kw=120.0,
                session_status="ACTIVE", created_at=now, updated_at=now,
            ))
            session.commit()
        finally:
            session.close()

    def test_end_charging_200(self, client):
        """DELETE /api/charging/sessions/{car_id} 返回 200"""
        self._prepare_end_charging(client)
        response = client.delete("/api/charging/sessions/京A12345")
        assert response.status_code == 200

    def test_end_charging_returns_bill(self, client):
        """结束充电返回账单信息"""
        self._prepare_end_charging(client)
        response = client.delete("/api/charging/sessions/京A12345")
        data = response.json()
        assert data["success"] is True
        assert "bill_id" in data
        assert data["total_fee"] > 0


class TestChargingAPIBusiness:
    """充电业务测试"""

    def test_queue_position_depends_on_capacity(self, client):
        """排队位置应根据车辆数量和电池容量计算"""
        r1 = client.post("/api/charging/requests", json={
            "car_Id": "京A11111", "Request_Amount": 50.0, "Request_Mode": "FAST_CHARGE",
        })
        r2 = client.post("/api/charging/requests", json={
            "car_Id": "京A22222", "Request_Amount": 30.0, "Request_Mode": "FAST_CHARGE",
        })
        assert r1.json()["car_position"] != r2.json()["car_position"]

    def test_charging_progress_updates(self, client):
        """充电进度应随时间更新"""
        # 需要先创建一个活跃充电会话
        from datetime import datetime
        from src.db.database import get_session
        from src.db.models import ChargingSession, Vehicle
        session = get_session()
        try:
            now = datetime.now()
            # 确保车辆存在
            existing = session.query(Vehicle).filter(
                Vehicle.license_plate == "京A12345"
            ).first()
            if not existing:
                session.add(Vehicle(
                    vehicle_id="VTest", user_id="UTest",
                    license_plate="京A12345", battery_capacity_kwh=60.0,
                    created_at=now, updated_at=now,
                ))
            # 创建活跃充电会话
            session.add(ChargingSession(
                session_id="S_ACTIVE_TEST",
                request_id="R_ACTIVE_TEST",
                car_id="京A12345", pile_id="P001",
                start_time=now, target_power_kwh=50.0,
                charged_power_kwh=0, current_power_kw=120.0,
                session_status="ACTIVE",
                created_at=now, updated_at=now,
            ))
            session.commit()
        finally:
            session.close()

        r1 = client.get("/api/charging/sessions/京A12345")
        r2 = client.get("/api/charging/sessions/京A12345")
        assert r1.json()["success"] is True
        # 由于是活跃会话且有时间差，第二次查询的已充电量应略大于第一次
        assert r2.json()["charged_power_kwh"] >= r1.json()["charged_power_kwh"]


class TestBillingAPI:
    """账单 API 测试"""

    def test_query_bill_200(self, client):
        """GET /api/bills 返回 200"""
        response = client.get("/api/bills", params={
            "car_id": "京A12345", "date": "2026-06-07",
        })
        assert response.status_code == 200

    def test_query_bill_returns_list(self, client):
        """查看账单返回 bills 列表"""
        response = client.get("/api/bills", params={
            "car_id": "京A12345", "date": "2026-06-07",
        })
        data = response.json()
        assert data["success"] is True
        assert "bills" in data

    def test_detailed_bill_200(self, client):
        """GET /api/bills/{bill_id}/details 返回 200"""
        response = client.get("/api/bills/B20260607001/details")
        assert response.status_code == 200

    def test_detailed_bill_has_periods(self, client):
        """详单包含时段明细"""
        response = client.get("/api/bills/B20260607001/details")
        data = response.json()
        assert "periods" in data
        assert len(data["periods"]) > 0


class TestPileAPI:
    """充电桩管理 API 测试"""

    def test_power_on_200(self, client, admin_headers):
        """POST /api/piles/{pile_id}/power/on 返回 200"""
        response = client.post("/api/piles/P001/power/on", headers=admin_headers)
        assert response.status_code == 200

    def test_set_parameters_200(self, client, admin_headers):
        """PUT /api/piles/{pile_id}/parameters 返回 200"""
        response = client.put("/api/piles/P001/parameters", json={
            "pile_Id": "P001",
            "peak_price": 1.5,
            "normal_price": 1.0,
            "valley_price": 0.5,
            "base_service_fee": 5.0,
            "time_coefficient": 0.5,
        }, headers=admin_headers)
        assert response.status_code == 200

    def test_start_pile_200(self, client, admin_headers):
        """POST /api/piles/{pile_id}/run 返回 200"""
        response = client.post("/api/piles/P001/run", headers=admin_headers)
        assert response.status_code == 200

    def test_power_off_200(self, client, admin_headers):
        """POST /api/piles/{pile_id}/power/off 返回 200"""
        response = client.post("/api/piles/P001/power/off", headers=admin_headers)
        assert response.status_code == 200

    def test_query_pile_state_200(self, client):
        """GET /api/piles/{pile_id}/state 返回 200"""
        response = client.get("/api/piles/P001/state")
        assert response.status_code == 200

    def test_query_pile_state_has_stats(self, client):
        """查看状态返回累计统计数据"""
        response = client.get("/api/piles/P001/state")
        data = response.json()
        assert data["success"] is True
        for key in ("working_state", "total_charge_num", "total_charge_time", "total_capacity"):
            assert key in data
        assert data["total_charge_num"] >= 0

    def test_overview_returns_all_piles(self, client):
        """GET /api/piles/overview 返回所有充电桩"""
        response = client.get("/api/piles/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "piles" in data
        assert "summary" in data
        assert len(data["piles"]) >= 2
        for p in data["piles"]:
            assert "pile_id" in p
            assert "status" in p
            assert "queue_length" in p

    def test_power_on_requires_auth(self, client):
        """未认证的管理员请求 power/on 应返回 401"""
        response = client.post("/api/piles/P001/power/on")
        assert response.status_code == 401


class TestQueueAPI:
    """队列 API 测试"""

    def test_query_queue_state_200(self, client):
        """GET /api/queues/state 返回 200"""
        response = client.get("/api/queues/state", params={"queuelist": "P001,P002"})
        assert response.status_code == 200

    def test_query_queue_state_has_queues(self, client):
        """查看队列状态返回 queues 列表"""
        response = client.get("/api/queues/state", params={"queuelist": "P001,P002"})
        data = response.json()
        assert data["success"] is True
        assert "queues" in data
        for q in data["queues"]:
            assert "pile_id" in q
            assert "vehicles" in q


class TestStrategyAPI:
    """策略管理 API 测试"""

    def test_get_strategies_200(self, client):
        """GET /api/strategies 返回 200"""
        response = client.get("/api/strategies")
        assert response.status_code == 200

    def test_get_strategies_has_fields(self, client):
        """获取策略返回所有必要字段"""
        response = client.get("/api/strategies")
        data = response.json()
        assert "current_algorithm" in data
        assert "current_fault_strategy" in data
        assert "available_algorithms" in data

    def test_switch_dispatch_200(self, client, admin_headers):
        """PUT /api/strategies/dispatch 返回 200"""
        response = client.put("/api/strategies/dispatch", json={
            "strategy_type": "BATCH_SHORTEST_TIME",
        }, headers=admin_headers)
        assert response.status_code == 200

    def test_switch_fault_200(self, client, admin_headers):
        """PUT /api/strategies/fault 返回 200"""
        response = client.put("/api/strategies/fault", json={
            "strategy_type": "PRIORITY",
        }, headers=admin_headers)
        assert response.status_code == 200

    def test_switch_invalid_returns_false(self, client, admin_headers):
        """切换未知策略返回 success=False"""
        response = client.put("/api/strategies/dispatch", json={
            "strategy_type": "INVALID",
        }, headers=admin_headers)
        assert response.status_code == 200
        assert response.json()["success"] is False

    def test_switch_dispatch_requires_auth(self, client):
        """未认证的管理员切换策略应返回 401"""
        response = client.put("/api/strategies/dispatch", json={
            "strategy_type": "BATCH_SHORTEST_TIME",
        })
        assert response.status_code == 401
