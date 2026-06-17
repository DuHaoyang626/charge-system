"""
管理端 — 报表统计路由
"""
from fastapi import APIRouter, Depends, Query

from core.deps import get_current_admin
from core.response import resp_err, resp_ok
from service.admin.service import (
    get_charging_volume_report,
    get_revenue_report,
    get_utilization_report,
)

router = APIRouter(tags=["管理端-报表"])


@router.get("/admin/reports/charging-volume")
async def admin_charging_volume(
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    granularity: str = Query("month", alias="granularity"),
    admin_id: int = Depends(get_current_admin),
):
    """充电量统计。"""
    if not start_date or not end_date:
        return resp_err(400, "缺少必填参数 startDate / endDate")
    if granularity not in ("day", "week", "month"):
        return resp_err(400, "granularity 必须是 day / week / month")
    data = get_charging_volume_report(
        start_date=start_date, end_date=end_date, granularity=granularity,
    )
    return resp_ok(data=data)


@router.get("/admin/reports/revenue")
async def admin_revenue(
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    granularity: str = Query("month", alias="granularity"),
    admin_id: int = Depends(get_current_admin),
):
    """收入统计。"""
    if not start_date or not end_date:
        return resp_err(400, "缺少必填参数 startDate / endDate")
    if granularity not in ("day", "week", "month"):
        return resp_err(400, "granularity 必须是 day / week / month")
    data = get_revenue_report(
        start_date=start_date, end_date=end_date, granularity=granularity,
    )
    return resp_ok(data=data)


@router.get("/admin/reports/utilization")
async def admin_utilization(
    start_date: str | None = Query(None, alias="startDate"),
    end_date: str | None = Query(None, alias="endDate"),
    admin_id: int = Depends(get_current_admin),
):
    """充电桩利用率。"""
    if not start_date or not end_date:
        return resp_err(400, "缺少必填参数 startDate / endDate")
    data = get_utilization_report(start_date=start_date, end_date=end_date)
    return resp_ok(data=data)
