"""
充电桩管理/策略切换 — Pydantic Schema
对应 API: /api/piles, /api/strategies
"""

from pydantic import Field

from src.schemas import ApiBaseModel


# ── 充电桩管理 ─────────────────────────────────────────

class SetParametersRequest(ApiBaseModel):
    """setParameters(pile_Id, 计费规则, 峰时电价, 平时电价, 谷时电价)"""
    pile_id: str = Field(..., description="充电桩编号", alias="pile_Id")
    peak_price: float = Field(..., gt=0, description="峰时电价(元/kWh)")
    normal_price: float = Field(..., gt=0, description="平时电价(元/kWh)")
    valley_price: float = Field(..., gt=0, description="谷时电价(元/kWh)")
    base_service_fee: float = Field(default=5.0, description="基础服务费(元)")
    time_coefficient: float = Field(default=0.5, description="时长系数(元/分钟)")


class PileStateResponse(ApiBaseModel):
    """Query_PileState 返回"""
    pile_id: str
    working_state: str
    total_charge_num: int
    total_charge_time: float
    total_capacity: float


# ── 策略管理 ───────────────────────────────────────────

class CurrentStrategiesResponse(ApiBaseModel):
    """getCurrentStrategies() 返回"""
    current_algorithm: str
    current_fault_strategy: str
    available_algorithms: list[str]
    available_fault_strategies: list[str]


class SwitchStrategyRequest(ApiBaseModel):
    """switchDispatchStrategy / switchFaultStrategy"""
    strategy_type: str = Field(..., description="策略标识符")
