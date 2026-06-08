"""
集成测试 — 跨服务交互场景

框架测试（PASS）：接口协作正常
业务测试（xfail）：全流程数据一致性依赖真实逻辑
"""

import pytest


class TestIntegrationFramework:
    """框架层面：服务之间协作正常"""

    def test_account_to_dispatch_flow(self, account_service, dispatch_service):
        # 注册
        reg = account_service.create_account("京A12345", "张三", 60.0)
        assert reg["success"] is True
        user_id = reg["user_id"]

        # 设置密码（真实实现要求 set_password 后才能登录）
        pwd = account_service.set_password(user_id, "Abc12345")
        assert pwd["success"] is True

        # 登录
        login = account_service.authenticate("京A12345", "Abc12345")
        assert login["success"] is True

        dispatch = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert dispatch["success"] is True
        assert "pile_id" in dispatch

    def test_dispatch_to_billing_flow(self, dispatch_service, billing_service):
        dispatch = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert dispatch["success"] is True

        bill = billing_service.calculate_bill("S20260607001")
        assert bill["success"] is True
        assert bill["total_fee"] > 0

    def test_fault_reschedule_chain(self, dispatch_service):
        vehicles = [
            {"car_id": "京A12345", "zone_type": "CHARGING_AREA", "membership_level": 2},
            {"car_id": "京B67890", "zone_type": "WAITING_AREA", "membership_level": 0},
        ]
        result = dispatch_service.reschedule_by_priority(vehicles)
        assert len(result) >= 1
        assert result[0]["success"] is True

    def test_billing_detailed_then_bill(self, billing_service):
        """详单和账单数据可达"""
        bill = billing_service.calculate_bill("S20260607001")
        detail = billing_service.get_detailed_bill(bill["bill_id"])
        assert len(detail["periods"]) > 0

    def test_monitor_collects_all_piles(self, monitor_service):
        """批量采集应返回配置文件中所有充电桩状态"""
        from src.config import config
        from src.main import _sync_piles_from_config

        _sync_piles_from_config()
        stats = monitor_service.batch_collect_stats()
        assert len(stats) == len(config.piles), (
            f"batch_collect_stats 应返回全部 {len(config.piles)} 个充电桩, "
            f"实际返回 {len(stats)} 个"
        )

        # 验证返回结构一致
        if stats:
            first = stats[0]
            for key in ("working_state", "total_charge_num",
                        "total_charge_time", "total_capacity",
                        "current_charging_count", "status"):
                assert key in first, f"返回结果缺少字段: {key}"

    def test_queue_zone_progression(self, queue_service):
        """三区单向流转：排队区 -> 等待区 -> 充电区"""
        enq = queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        assert enq["success"] is True

        state = queue_service.get_car_state("京A12345")
        assert state["zone_type"] == "QUEUE_AREA"

        deq = queue_service.dequeue("P001")
        assert deq["success"] is True

        state2 = queue_service.get_car_state("京A12345")
        assert state2["zone_type"] == "WAITING_AREA"


class TestIntegrationBusiness:
    """业务层面：完整流程的数据一致性"""

    def test_full_charging_flow_data_consistency(self, account_service, dispatch_service, billing_service):
        """一次完整充电的数据一致性

        预期：50kWh @120kW 10:00-11:00 峰时 → 电费 75 + 服务费 35 = 110
        """
        account_service.create_account("京A12345", "张三", 60.0)
        dispatch = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert dispatch["pile_id"] is not None

        bill = billing_service.calculate_bill("S20260607001")
        period_sum = sum(p["subtotal_fee"] for p in bill["periods"])
        assert abs(period_sum - bill["total_fee"]) < 0.01
        assert bill["total_fee"] == pytest.approx(110.0, rel=0.1)

    def test_billing_payment_flow(self, billing_service):
        """账单 -> 支付流程"""
        from src.services.payment_service import PaymentService
        pay_svc = PaymentService()

        # 生成账单
        bill = billing_service.calculate_bill("S20260607001")
        assert bill["payment_status"] == "UNPAID"

        # 支付
        result = pay_svc.pay_bill(bill["bill_id"])
        assert result["success"] is True
        assert result["payment_status"] == "PAID"

        # 验证账单状态已更新
        bill2 = billing_service.get_detailed_bill(bill["bill_id"])
        assert bill2["payment_status"] == "PAID"

