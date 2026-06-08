"""
计费服务单元测试

框架测试（PASS）：接口存在、返回值结构
业务测试（xfail）：费用计算、时段拆分依赖真实逻辑
"""

import pytest


class TestBillingServiceFramework:
    """框架层面：接口可调用、返回值结构正常"""

    def test_calculate_bill_returns_bill_id(self, billing_service):
        result = billing_service.calculate_bill("S20260607001")
        assert result["success"] is True
        assert "bill_id" in result

    def test_calculate_bill_has_fees(self, billing_service):
        result = billing_service.calculate_bill("S20260607001")
        assert result["total_charge_fee"] > 0
        assert result["total_service_fee"] >= 0

    def test_calculate_bill_has_periods(self, billing_service):
        result = billing_service.calculate_bill("S20260607001")
        assert "periods" in result
        assert len(result["periods"]) > 0
        for p in result["periods"]:
            assert "period_name" in p

    def test_query_bill_by_date_returns_list(self, billing_service):
        bills = billing_service.query_bill_by_date("京A12345", "2026-06-07")
        assert isinstance(bills, list)

    def test_get_detailed_bill_has_periods(self, billing_service):
        detail = billing_service.get_detailed_bill("B20260607001")
        assert "bill_id" in detail
        assert "periods" in detail
        assert len(detail["periods"]) > 0

    def test_bill_consistency(self, billing_service):
        """同一账单多次查询结果一致"""
        r1 = billing_service.calculate_bill("S20260607001")
        r2 = billing_service.calculate_bill("S20260607001")
        assert r1["bill_id"] == r2["bill_id"]

    def test_empty_date_returns_list(self, billing_service):
        bills = billing_service.query_bill_by_date("京A99999", "2020-01-01")
        assert isinstance(bills, list)


class TestBillingServiceBusiness:
    """业务层面：费用计算正确性"""

    def test_bill_total_equals_period_sum(self, billing_service):
        result = billing_service.calculate_bill("S20260607001")
        period_sum = sum(p["subtotal_fee"] for p in result["periods"])
        assert abs(period_sum - result["total_fee"]) < 0.01

    def test_bill_amount_matches_session(self, billing_service):
        """费用应与充电量 × 对应时段电价匹配"""
        result = billing_service.calculate_bill("S20260607001")
        # session: 10:00-11:00 峰时电价 1.5 元/kWh, 50kWh
        assert result["total_charge_fee"] == pytest.approx(75.0, rel=0.1)
        # 服务费 = 5 + 0.5 × 60 = 35
        assert result["total_service_fee"] == pytest.approx(35.0, rel=0.1)
        # 总费用 = 75 + 35 = 110
        assert result["total_fee"] == pytest.approx(110.0, rel=0.1)

    def test_empty_date_returns_empty(self, billing_service):
        """不存在日期应返回空列表"""
        bills = billing_service.query_bill_by_date("京A99999", "2020-01-01")
        assert len(bills) == 0
