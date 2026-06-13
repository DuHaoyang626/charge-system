"""
账单模块路由 — 列表、详情、支付。
"""
from fastapi import APIRouter, Depends, Query

from core.deps import get_current_user
from core.exceptions import AppException, Err
from core.response import resp_err, resp_ok
from service.billing.service import get_bill, get_user_bills, process_payment

router = APIRouter(tags=["账单"])


@router.get("/bills")
async def api_list_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    payment_status: str | None = Query(None, alias="paymentStatus"),
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    user_id: int = Depends(get_current_user),
):
    """获取我的历史账单（分页）。"""
    data = get_user_bills(
        user_id=user_id,
        page=page,
        page_size=page_size,
        payment_status=payment_status,
        start_date=start_date,
        end_date=end_date,
    )
    return resp_ok(data=data)


@router.get("/bills/{bill_id}")
async def api_get_bill(
    bill_id: int,
    user_id: int = Depends(get_current_user),
):
    """获取账单详情。"""
    result = get_bill(bill_id, user_id=user_id)
    if result is None:
        raise AppException(*Err.BILL_NOT_FOUND)
    return resp_ok(data=result)


@router.post("/bills/{bill_id}/pay")
async def api_pay_bill(
    bill_id: int,
    body: dict,
    user_id: int = Depends(get_current_user),
):
    """模拟支付。"""
    payment_method = body.get("paymentMethod", "")
    if not payment_method:
        return resp_err(400, "请选择支付方式")
    result = process_payment(bill_id, user_id, payment_method)
    return resp_ok(data=result, message="支付成功")
