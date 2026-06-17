"""
管理端 — 账单管理路由
"""
from fastapi import APIRouter, Depends, Query

from core.deps import get_current_admin
from core.exceptions import AppException, Err
from core.response import resp_ok
from service.admin.service import list_all_bills, get_admin_bill_detail

router = APIRouter(tags=["管理端-账单"])


@router.get("/admin/bills")
async def admin_list_bills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    user_id: int | None = Query(None, alias="userId"),
    license_plate: str | None = Query(None, alias="licensePlate"),
    station_id: int | None = Query(None, alias="stationId"),
    payment_status: str | None = Query(None, alias="paymentStatus"),
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    admin_id: int = Depends(get_current_admin),
):
    """查看所有账单（分页）。"""
    data = list_all_bills(
        page=page, page_size=page_size,
        user_id=user_id, license_plate=license_plate,
        station_id=station_id, payment_status=payment_status,
        start_date=start_date, end_date=end_date,
    )
    return resp_ok(data=data)


@router.get("/admin/bills/{bill_id}")
async def admin_get_bill(
    bill_id: int,
    admin_id: int = Depends(get_current_admin),
):
    """查看任意账单详情。"""
    data = get_admin_bill_detail(bill_id)
    if data is None:
        raise AppException(*Err.NOT_FOUND)
    return resp_ok(data=data)
