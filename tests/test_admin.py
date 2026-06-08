"""
管理员功能测试 — UC-16 移动车辆、UC-20 运营报表
"""

from datetime import datetime

from src.db.database import get_session
from src.db.models import ChargingRequest


class TestMoveVehicle:
    """UC-16: 管理员移动车辆"""

    def test_move_vehicle_success(self, client):
        """移动车辆到其他充电桩排队区"""
        from src.db.database import get_session
        from src.db.models import ChargingRequest

        # 先创建一条充电请求
        session = get_session()
        try:
            session.add(ChargingRequest(
                request_id="R_MOVE_TEST",
                car_id="京A12345",
                pile_id="P001",
                request_time=datetime.now(),
                charging_mode="FAST_CHARGE",
                target_power_kwh=50.0,
                request_status="QUEUED",
                zone_type="QUEUE_AREA",
                queue_position=1,
                is_active=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ))
            session.commit()
        finally:
            session.close()

        response = client.put(
            "/api/admin/vehicles/京A12345/move"
            "?target_pile_id=P002&target_zone=QUEUE_AREA&target_position=2"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["new_pile_id"] == "P002"
        assert data["new_zone"] == "QUEUE_AREA"
        assert data["new_position"] == 2

    def test_move_vehicle_invalid_zone(self, client):
        """移动车辆到无效区域应返回错误"""
        response = client.put(
            "/api/admin/vehicles/京A12345/move"
            "?target_pile_id=P001&target_zone=INVALID_ZONE&target_position=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_move_vehicle_nonexistent_pile(self, client):
        """移动车辆到不存在的充电桩应返回错误"""
        response = client.put(
            "/api/admin/vehicles/京A12345/move"
            "?target_pile_id=P999&target_zone=QUEUE_AREA&target_position=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_move_vehicle_no_active_request(self, client):
        """移动无活跃请求的车辆应返回错误"""
        response = client.put(
            "/api/admin/vehicles/京A99999/move"
            "?target_pile_id=P001&target_zone=QUEUE_AREA&target_position=1"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestReports:
    """UC-20: 运营报表"""

    def test_generate_report_success(self, client):
        """生成运营报表成功"""
        response = client.get("/api/admin/reports")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "report" in data
        report = data["report"]
        assert "summary" in report
        assert "pile_details" in report
        assert "total_charge_capacity_kwh" in report["summary"]
        assert "total_revenue" in report["summary"]
        assert "total_sessions" in report["summary"]

    def test_report_pile_details(self, client):
        """报表应包含每个充电桩的明细"""
        response = client.get("/api/admin/reports")
        data = response.json()
        assert len(data["report"]["pile_details"]) >= 2
        for p in data["report"]["pile_details"]:
            assert "pile_id" in p
            assert "total_charge_num" in p

    def test_report_with_date_range(self, client):
        """报表支持日期范围筛选"""
        response = client.get(
            "/api/admin/reports?start_date=2026-01-01&end_date=2026-12-31"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["report"]["period"]["start"] == "2026-01-01"
