
"""
调度服务 + 调度策略 单元测试

框架测试（PASS）：策略切换、参数校验
业务测试（xfail）：分配算法、故障调度逻辑未实现
"""

import pytest


class TestDispatchServiceFramework:
    """框架层面：接口存在"""

    def test_assign_pile_returns_result(self, dispatch_service):
        """分配充电桩返回结果"""
        result = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert isinstance(result, dict)
        assert "success" in result
        assert "pile_id" in result

    def test_reschedule_by_priority_returns_list(self, dispatch_service):
        """优先级调度返回列表"""
        result = dispatch_service.reschedule_by_priority([
            {"car_id": "京A12345", "zone_type": "CHARGING_AREA"},
        ])
        assert isinstance(result, list)

    def test_reschedule_by_time_order_returns_list(self, dispatch_service):
        """时间顺序调度返回列表"""
        result = dispatch_service.reschedule_by_time_order([
            {"car_id": "京A12345", "request_time": "2026-06-07T08:00:00"},
        ])
        assert isinstance(result, list)

    def test_fault_recovery_returns_dict(self, dispatch_service):
        """故障恢复返回结果"""
        result = dispatch_service.recover_charging_fault("P001")
        assert result["success"] is True

    def test_shortest_total_time_returns_list(self, dispatch_service):
        """单次最短调度返回列表"""
        result = dispatch_service.reschedule_by_shortest_total_time([
            {"car_id": "京A12345", "request_amount": 60.0},
        ])
        assert isinstance(result, list)

    def test_batch_assign_returns_list(self, dispatch_service):
        """批量调度返回列表"""
        result = dispatch_service.batch_assign_by_shortest_total_time(
            [{"car_id": "京A12345", "request_amount": 60.0}],
            [{"pile_id": "P001", "max_power_kw": 120.0, "type": "fast_charge"}],
        )
        assert isinstance(result, list)


class TestDispatchServiceBusiness:
    """业务层面：调度算法正确性"""

    def test_assign_chooses_fastest_pile(self, dispatch_service):
        """分配应选择总时间最短的充电桩"""
        result = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        # 如果有空闲桩，充电时间 = 50/120 = 0.42h = 25 分钟
        # mock 固定返回 55.5 分钟，但真实计算应为约 25 分钟
        assert result["estimated_total_minutes"] == pytest.approx(25.0, rel=0.2)

    def test_priority_scheduling_order(self, dispatch_service):
        """优先级调度：充电中 > 等待区 > 排队区"""
        vehicles = [
            {"car_id": "京A", "zone_type": "QUEUE_AREA", "membership_level": 3},
            {"car_id": "京B", "zone_type": "CHARGING_AREA", "membership_level": 0},
            {"car_id": "京C", "zone_type": "WAITING_AREA", "membership_level": 1},
        ]
        result = dispatch_service.reschedule_by_priority(vehicles)
        assert len(result) == 3
        assert result[0]["car_id"] == "京B"

    def test_hungarian_optimal_assignment(self, dispatch_service):
        """匈牙利算法应求全局最优"""
        result = dispatch_service.batch_assign_by_shortest_total_time(
            [{"car_id": "京A", "request_amount": 80.0},
             {"car_id": "京B", "request_amount": 30.0},
             {"car_id": "京C", "request_amount": 20.0}],
            [{"pile_id": "P1", "max_power_kw": 60.0, "type": "fast_charge"},
             {"pile_id": "P2", "max_power_kw": 120.0, "type": "fast_charge"},
             {"pile_id": "P3", "max_power_kw": 120.0, "type": "fast_charge"}],
        )
        # TODO: 验证分配方案的总完成时间最小
        assert len(result) == 3


class TestDispatchStrategyFramework:
    """策略管理框架测试"""

    def test_init_defaults(self, dispatch_strategy):
        """初始化使用默认策略"""
        assert dispatch_strategy.get_current_algorithm() == "SHORTEST_TOTAL_TIME"
        assert dispatch_strategy.get_current_fault_strategy() == "TIME_ORDER"

    def test_switch_algorithm_invalid(self, dispatch_strategy):
        """切换无效策略应返回失败"""
        result = dispatch_strategy.switch_algorithm("INVALID")
        assert result["success"] is False
        # 策略不变
        assert dispatch_strategy.get_current_algorithm() == "SHORTEST_TOTAL_TIME"

    def test_switch_fault_invalid(self, dispatch_strategy):
        """切换无效故障策略应返回失败"""
        result = dispatch_strategy.switch_fault("INVALID")
        assert result["success"] is False

    def test_get_status_has_lists(self, dispatch_strategy):
        """状态包含可用策略列表"""
        status = dispatch_strategy.get_status()
        assert "available_algorithms" in status
        assert "available_fault_strategies" in status
        assert len(status["available_algorithms"]) >= 2
        assert len(status["available_fault_strategies"]) >= 5


class TestDispatchStrategyBusiness:
    """策略管理业务测试"""

    def test_switch_algorithm_persists(self, dispatch_strategy):
        """策略切换应写入 dispatch_strategy_logs 表"""
        dispatch_strategy.switch_algorithm("BATCH_SHORTEST_TIME")
        # 验证日志表中有记录
        from src.db.database import get_session
        from src.db.models import DispatchStrategyLog
        session = get_session()
        try:
            log = session.query(DispatchStrategyLog).filter(
                DispatchStrategyLog.change_type == "ALGORITHM"
            ).order_by(DispatchStrategyLog.id.desc()).first()
            assert log is not None
            assert log.from_value == "SHORTEST_TOTAL_TIME"
            assert log.to_value == "BATCH_SHORTEST_TIME"
        finally:
            session.close()

    def test_switch_affects_dispatch(self, dispatch_service, dispatch_strategy):
        """切换策略应影响后续分配结果"""
        dispatch_strategy.switch_algorithm("BATCH_SHORTEST_TIME")
        result = dispatch_service.assign_charging_pile("京A12345", 50.0, "FAST_CHARGE")
        assert result["success"] is True
