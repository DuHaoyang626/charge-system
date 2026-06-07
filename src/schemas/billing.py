"""
账单/详单/支付 — Pydantic Schema
对应 API: /api/bills
"""

from datetime import date, datetime

from pydantic import Field

from src.schemas import ApiBaseModel


class BillItem(ApiBaseModel):
    """Request_Bill 返回的单条账单概览"""
    car_id: str
    date: date
    bill_id: str
    charge_pile_num: str
    charge_amount: float
    charge_duration: float
    start_time: datetime
    end_time: datetime
    total_charge_fee: float
    total_service_fee: float
    total_fee: float


class BillListResponse(ApiBaseModel):
    """Request_Bill 响应：账单列表"""
    bills: list[BillItem]


class PeriodDetail(ApiBaseModel):
    """分时段费用明细"""
    period_name: str
    charge_fee: float
    service_fee: float
    subtotal_fee: float


class DetailedBillResponse(ApiBaseModel):
    """Request_DetailedList 返回"""
    car_id: str
    date: date
    bill_id: str
    charge_pile_num: str
    charge_amount: float
    charge_duration: float
    start_time: datetime
    end_time: datetime
    periods: list[PeriodDetail]
