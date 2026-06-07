"""
充电请求/会话/队列 — Pydantic Schema
对应 API: /api/charging, /api/queues
"""

from datetime import datetime

from pydantic import Field

from src.schemas import ApiBaseModel


# ── 充电请求 ───────────────────────────────────────────

class ChargingRequestRequest(ApiBaseModel):
    """E_chargingRequest(car_Id, Request_Amount, Request_Mode)"""
    car_id: str = Field(..., description="车牌号", alias="car_Id")
    request_amount: float = Field(..., gt=0, description="请求电量(kWh)", alias="Request_Amount")
    request_mode: str = Field(..., description="充电模式 FAST_CHARGE/SLOW_CHARGE", alias="Request_Mode")


class ModifyAmountRequest(ApiBaseModel):
    """Modify_Amount(car_Id, Amount)"""
    car_id: str = Field(..., description="车牌号", alias="car_Id")
    amount: float = Field(..., gt=0, description="新电量(kWh)", alias="Amount")


class ModifyModeRequest(ApiBaseModel):
    """Modify_Mode(car_Id, Mode)"""
    car_id: str = Field(..., description="车牌号", alias="car_Id")
    mode: str = Field(..., description="新充电模式 FAST_CHARGE/SLOW_CHARGE", alias="Mode")


# ── 充电会话 ───────────────────────────────────────────

class StartChargingRequest(ApiBaseModel):
    """Start_Charging(car_id, ChargePileNum)"""
    car_id: str = Field(..., description="车牌号")
    charge_pile_num: str = Field(..., description="充电桩编号", alias="ChargePileNum")


class EndChargingRequest(ApiBaseModel):
    """End_Charging(car_id, ChargingPileNum)"""
    car_id: str = Field(..., description="车牌号")
    charging_pile_num: str = Field(..., description="充电桩编号", alias="ChargingPileNum")


# ── 响应体 ─────────────────────────────────────────────

class ChargingRequestResponse(ApiBaseModel):
    """Return(car_position, car_state, queue_Num, request_time)"""
    car_position: int
    car_state: str
    queue_num: str
    request_time: datetime


class QueryCarStateResponse(ApiBaseModel):
    """Return(car_Number_before_position, car_state, queue_Num, request_time)"""
    car_number_before_position: int
    car_state: str
    queue_num: str
    request_time: datetime


class ChargingStateResponse(ApiBaseModel):
    """Return(详单信息)"""
    car_id: str
    pile_id: str
    session_id: str
    current_battery_percentage: float
    charged_power_kwh: float
    current_power_kw: float
    estimated_remaining_minutes: float
    current_period_price: float
    accumulated_fee: float
    start_time: datetime
