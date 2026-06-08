"""
支付服务单元测试
"""

from src.db.database import get_session
from src.db.models import PaymentOrder


def test_pay_bill_success(billing_service):
    """支付账单成功"""
    from src.services.payment_service import PaymentService
    pay_svc = PaymentService()

    bill = billing_service.calculate_bill("S20260607001")
    result = pay_svc.pay_bill(bill["bill_id"])

    assert result["success"] is True
    assert result["payment_status"] == "PAID"
    assert "order_id" in result
    assert result["total_amount"] == bill["total_fee"]


def test_pay_bill_idempotent(billing_service):
    """已支付账单重复支付应返回成功"""
    from src.services.payment_service import PaymentService
    pay_svc = PaymentService()

    bill = billing_service.calculate_bill("S20260607001")

    r1 = pay_svc.pay_bill(bill["bill_id"])
    assert r1["success"] is True

    r2 = pay_svc.pay_bill(bill["bill_id"])
    assert r2["success"] is True


def test_pay_bill_not_found(_db):
    """支付不存在的账单应返回失败"""
    from src.services.payment_service import PaymentService
    result = PaymentService().pay_bill("B00000000")
    assert result["success"] is False
    assert "账单不存在" in result["message"]


def test_pay_creates_payment_order(billing_service):
    """支付后应生成支付订单记录"""
    from src.services.payment_service import PaymentService
    pay_svc = PaymentService()

    bill = billing_service.calculate_bill("S20260607001")
    result = pay_svc.pay_bill(bill["bill_id"])

    session = get_session()
    try:
        order = session.query(PaymentOrder).filter(
            PaymentOrder.bill_id == bill["bill_id"]
        ).first()
        assert order is not None
        assert order.payment_status == "PAID"
        assert float(order.total_amount) == bill["total_fee"]
    finally:
        session.close()
