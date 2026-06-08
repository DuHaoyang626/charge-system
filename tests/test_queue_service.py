"""
队列服务单元测试

框架测试（PASS）：接口可调用、返回值结构、基本队列操作
业务测试（xfail）：等待时间计算依赖 target_power_kwh 传入
"""

import pytest


class TestQueueServiceFramework:
    """框架层面：接口存在、返回值结构正常、基本队列操作"""

    def test_enqueue_returns_dict(self, queue_service):
        """入队方法可调用且返回 dict"""
        result = queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        assert isinstance(result, dict)
        assert "success" in result
        assert "queue_position" in result
        assert "pile_id" in result

    def test_enqueue_returns_position(self, queue_service):
        """入队返回正数的排队位置"""
        result = queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        assert result["queue_position"] > 0

    def test_enqueue_rejects_invalid_pile(self, queue_service):
        """不存在的充电桩应拒绝入队"""
        result = queue_service.enqueue("京A12345", "P999", "FAST_CHARGE")
        assert result["success"] is False
        assert "不存在" in result["message"]

    def test_dequeue_returns_car(self, queue_service):
        """出队返回车辆信息和目标区"""
        queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        result = queue_service.dequeue("P001")
        assert result["success"] is True
        assert "car_id" in result
        assert result["to_zone"] == "WAITING_AREA"

    def test_dequeue_empty_queue(self, queue_service):
        """空队列出队应返回失败"""
        result = queue_service.dequeue("P001")
        assert result["success"] is False
        assert "无车辆" in result["message"]

    def test_change_queue_switches_pile(self, queue_service):
        """换队返回新的充电桩编号"""
        queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        result = queue_service.change_queue("京A12345", "P001", "P002")
        assert result["success"] is True
        assert result["new_pile_id"] == "P002"

    def test_change_queue_invalid_car(self, queue_service):
        """不存在的车辆换队应返回失败"""
        result = queue_service.change_queue("京A99999", "P001", "P002")
        assert result["success"] is False
        assert "不在" in result["message"]

    def test_get_car_state_has_keys(self, queue_service):
        """查询状态返回必要字段"""
        queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        result = queue_service.get_car_state("京A12345")
        assert result["success"] is True
        for key in ("car_state", "queue_num", "zone_type"):
            assert key in result

    def test_get_car_state_no_request(self, queue_service):
        """无活跃请求应返回失败"""
        result = queue_service.get_car_state("京A99999")
        assert result["success"] is False
        assert "无活跃请求" in result["message"]

    def test_get_queue_detail_structure(self, queue_service):
        """队列详情返回正确结构"""
        queue_service.enqueue("京A12345", "P001", "FAST_CHARGE")
        results = queue_service.get_queue_detail(["P001"])
        assert isinstance(results, list)
        assert len(results) > 0
        for q in results:
            assert "pile_id" in q
            assert "vehicles" in q
            for v in q["vehicles"]:
                assert "car_id" in v
                assert "battery_capacity_kwh" in v
                assert "request_amount_kwh" in v
                assert "wait_minutes" in v

    def test_get_queue_detail_empty_pile_ids(self, queue_service):
        """空列表查询返回空结果"""
        results = queue_service.get_queue_detail([])
        assert isinstance(results, list)
        assert len(results) == 0

    def test_get_queue_detail_unknown_pile(self, queue_service):
        """查询不存在的充电桩返回空结果"""
        results = queue_service.get_queue_detail(["P999"])
        assert isinstance(results, list)
        assert len(results) == 0

    # ── 原本在 xfail 中但现已可用的功能 ──

    def test_queue_position_increments(self, queue_service):
        """多次入队位置应递增"""
        pos1 = queue_service.enqueue("京A11111", "P001", "FAST_CHARGE")["queue_position"]
        pos2 = queue_service.enqueue("京A22222", "P001", "FAST_CHARGE")["queue_position"]
        assert pos2 > pos1

    def test_enqueue_rejects_when_full(self, queue_service):
        """排队区满时应拒绝入队"""
        MAX = 5  # test_config.yml: max_queue_capacity: 5
        for i in range(MAX):
            r = queue_service.enqueue(f"京A{i:05d}", "P001", "FAST_CHARGE")
            assert r["success"] is True

        # 第 6 辆应被拒绝
        r = queue_service.enqueue("京A99999", "P001", "FAST_CHARGE")
        assert r["success"] is False
        assert "排队区已满" in r["message"]

    def test_waiting_position_increments(self, queue_service):
        """等待区位置也应递增"""
        # 入队 3 辆车并依次出队到等待区
        for i in range(3):
            queue_service.enqueue(f"京A{i:05d}", "P001", "FAST_CHARGE")

        pos1 = queue_service.dequeue("P001")["position_in_waiting"]
        pos2 = queue_service.dequeue("P001")["position_in_waiting"]
        assert pos2 > pos1


class TestQueueServiceBusiness:
    """业务层面：等待时间计算"""

    def test_waiting_time_calculation(self, queue_service):
        """等待时间应根据前方车辆充电量实时计算"""
        # 第一辆车入队，前方无车 → 等待 0 分钟
        r1 = queue_service.enqueue("京A11111", "P001", "FAST_CHARGE", target_power_kwh=50.0)
        assert r1["estimated_wait_minutes"] == 0

        # 第二辆车入队，前方有 50kWh @ 120kW = 25 分钟
        r2 = queue_service.enqueue("京A22222", "P001", "FAST_CHARGE", target_power_kwh=30.0)
        assert r2["estimated_wait_minutes"] == pytest.approx(25.0, rel=0.1)

        # 第三辆车入队，前方 50+30 = 80kWh @ 120kW = 40 分钟
        r3 = queue_service.enqueue("京A33333", "P001", "FAST_CHARGE", target_power_kwh=20.0)
        assert r3["estimated_wait_minutes"] == pytest.approx(40.0, rel=0.1)
