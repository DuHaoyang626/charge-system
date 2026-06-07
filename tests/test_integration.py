"""
集成测试 — 跨服务交互场景

框架测试（PASS）：接口协作正常
业务测试（xfail）：全流程数据一致性依赖真实逻辑
"""

import pytest


class TestIntegrationFramework:
    """框架层面：服务之间协作正常"""

    def test_account_to_dispatch_flow(self, account_service, dispatch_service):
        reg = account_service.create_account("京A12345", "张三", 60.0)
        assert reg["success"] is True

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


@pytest.mark.xfail(reason="TODO: 全流程集成需要真实数据库和业务逻辑")
class TestIntegrationBusiness:
    """业务层面：完整流程的数据一致性"""

    def test_full_charging_flow_data_consistency(self, account_service, dispatch_service, billing_service):
        """一次完整充电的数据一致性

        预期：50kWh @120kW 峰时充电 → 电费 60 + 服务费 17.5 = 77.5
        """
        account_service.create_account("京A12345", "张三", 60.0)
        dispatch = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert dispatch["pile_id"] is not None

        bill = billing_service.calculate_bill("S20260607001")
        period_sum = sum(p["subtotal_fee"] for p in bill["periods"])
        assert abs(period_sum - bill["total_fee"]) < 0.01
        # mock 固定返回 58.1，但真实应为 77.5
        assert bill["total_fee"] == pytest.approx(77.5, rel=0.1)

    def test_queue_zone_progression(self, queue_service):
        """三区单向流转：排队区 -> 等待区 -> 充电区"""
        enq = queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        assert enq["success"] is True

        state = queue_service.get_car_state("京A12345")
        assert state["zone_type"] == "QUEUE_AREA", \
            "TODO: 入队后 zone_type 应为 QUEUE_AREA"

        deq = queue_service.dequeue("P001")
        assert deq["success"] is True

        state2 = queue_service.get_car_state("京A12345")
        assert state2["zone_type"] == "WAITING_AREA", \
            "TODO: 出队后 zone_type 应为 WAITING_AREA"

    def test_billing_payment_flow(self, billing_service):
        """账单 -> 支付流程"""
        bill = billing_service.calculate_bill("S20260607001")
        # TODO: mock 不维护支付状态
        assert bill["payment_status"] == "PAID", \
            "TODO: 支付完成后 payment_status 应更新为 PAID"

    def test_monitor_collects_all_piles(self, monitor_service):
        """批量采集应返回所有充电桩状态"""
        stats = monitor_service.batch_collect_stats()
        # TODO: mock 固定返回 2 条，配置中有 5 个桩
        assert len(stats) == 5, \
            "TODO: batch_collect_stats 应返回全部 5 个充电桩"
