"""
账单路由 — /api/bills

接口定义参考：docs/系统架构设计文档.md §5.1
覆盖用例：UC-12（查看账单）、UC-12a（查看详单）
"""

from fastapi import APIRouter, Query

from src.services.billing_service import BillingService

router = APIRouter(prefix="/api/bills", tags=["账单"])

_svc = BillingService()


@router.get("", summary="查看账单", response_model=dict)
def query_bill(car_id: str = Query(..., description="车牌号"),
               date: str = Query(..., description="日期 YYYY-MM-DD")):
    """Request_Bill(carId, date)

    查询指定日期指定用户的充电账单概览。

    **查询参数：**
    - `carId` (必填): 车牌号
    - `date` (必填): 日期，格式 YYYY-MM-DD

    **成功响应（有数据）：**
    ```json
    {
        "success": true,
        "bills": [
            {
                "bill_id": "B20260607001",
                "car_id": "京A12345",
                "date": "2026-06-07",
                "pile_id": "P001",
                "charge_amount": 45.5,
                "charge_duration_minutes": 60.0,
                "start_time": "2026-06-07T10:30:00",
                "end_time": "2026-06-07T11:30:00",
                "total_charge_fee": 45.6,
                "total_service_fee": 12.5,
                "total_fee": 58.1
            }
        ]
    }
    ```

    **成功响应（无数据）：**
    ```json
    {"success": true, "bills": []}
    ```
    """
    bills = _svc.query_bill_by_date(car_id, date)
    return {"success": True, "bills": bills}


@router.get("/{bill_id}/details", summary="查看详单", response_model=dict)
def query_detailed_bill(bill_id: str):
    """Request_DetailedList(Bill_Id)

    获取指定账单的分时段费用明细。

    **成功响应：**
    ```json
    {
        "success": true,
        "bill_id": "B20260607001",
        "car_id": "京A12345",
        "date": "2026-06-07",
        "pile_id": "P001",
        "charge_amount": 45.5,
        "charge_duration_minutes": 60.0,
        "start_time": "2026-06-07T10:30:00",
        "end_time": "2026-06-07T11:30:00",
        "periods": [
            {
                "period_name": "peak",
                "charge_kwh": 20.0,
                "unit_price": 1.2,
                "charge_fee": 24.0,
                "service_fee": 5.0,
                "subtotal_fee": 29.0
            },
            {
                "period_name": "normal",
                "charge_kwh": 25.5,
                "unit_price": 0.8,
                "charge_fee": 20.4,
                "service_fee": 7.5,
                "subtotal_fee": 27.9
            }
        ]
    }
    ```
    """
    detail = _svc.get_detailed_bill(bill_id)
    return {"success": True, **detail}
