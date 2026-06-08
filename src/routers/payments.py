"""
支付路由 — /api/payments

模拟支付接口，更新账单状态为 PAID
"""

from fastapi import APIRouter

from src.schemas.user import SimpleResponse
from src.services.payment_service import PaymentService

router = APIRouter(prefix="/api/payments", tags=["支付"])

_svc = PaymentService()


@router.post("/{bill_id}/pay", summary="支付账单", response_model=dict)
def pay_bill(bill_id: str):
    """支付指定账单

    模拟支付流程，将账单标记为已支付并生成支付订单记录。

    **参数：**
    - `bill_id` (路径): 账单编号

    **成功响应：**
    ```json
    {
        "success": true,
        "bill_id": "B20260607001",
        "payment_status": "PAID",
        "order_id": "P20260607001",
        "total_amount": 110.0
    }
    ```

    **失败响应：**
    ```json
    {"success": false, "message": "账单不存在"}
    ```
    """
    return _svc.pay_bill(bill_id)
