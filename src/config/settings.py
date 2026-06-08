"""
类型安全的配置数据类

与 config/application.yml 结构一一对应。
所有字段类型由 Pydantic 验证。
"""

from pydantic import BaseModel, Field


# ── 嵌套值对象 ─────────────────────────────────────────

class TimeRange(BaseModel):
    """时段区间 [start, end)"""
    start: str  # "HH:MM"
    end: str    # "HH:MM"


class TimePeriods(BaseModel):
    """峰/平/谷时段定义"""
    peak: list[TimeRange] = Field(default_factory=list)
    normal: list[TimeRange] = Field(default_factory=list)
    valley: list[TimeRange] = Field(default_factory=list)


class DefaultPrices(BaseModel):
    """默认三时段电价"""
    peak_price: float = 1.2
    normal_price: float = 0.8
    valley_price: float = 0.4


class ServiceFee(BaseModel):
    """服务费规则"""
    base_fee: float = 5.0
    time_coefficient: float = 0.5
    overtime_penalty: float = 0.8


class TimeoutConfig(BaseModel):
    """超时配置"""
    charging_confirm_timeout_seconds: int = 120
    timeout_base_fee: float = 5.0


class BillingConfig(BaseModel):
    """计费规则配置"""
    time_periods: TimePeriods = Field(default_factory=TimePeriods)
    default_prices: DefaultPrices = Field(default_factory=DefaultPrices)
    service_fee: ServiceFee = Field(default_factory=ServiceFee)
    timeout_config: TimeoutConfig = Field(default_factory=TimeoutConfig)


class DispatchConfig(BaseModel):
    """调度策略配置"""
    default_algorithm: str = "SHORTEST_TOTAL_TIME"
    default_fault_strategy: str = "TIME_ORDER"


class StationConfig(BaseModel):
    """充电站基本配置"""
    name: str = "智能充电站-01"
    max_queue_capacity: int = 50
    max_waiting_capacity: int = 5


class PileConfig(BaseModel):
    """单个充电桩硬件配置"""
    id: str
    name: str
    type: str  # fast_charge | slow_charge
    max_power_kw: float
    parking_spots: int = 1


class MonitoringConfig(BaseModel):
    """监控配置"""
    refresh_interval_seconds: int = 10


class AdminConfig(BaseModel):
    """管理员配置"""
    username: str = "admin"
    password: str = "admin123"


class LoggingConfig(BaseModel):
    """日志配置"""
    console_threshold: int = 1


class SystemConfig(BaseModel):
    """系统通用配置"""
    jwt_secret: str = "charge-system-jwt-secret-key-2026"
    token_expire_minutes: int = 1440
    db_path: str = "data/charge_system.db"


# ── 根配置 ─────────────────────────────────────────────

class AppSettings(BaseModel):
    """全系统配置聚合根，与 application.yml 结构一致"""
    station: StationConfig = Field(default_factory=StationConfig)
    piles: list[PileConfig] = Field(default_factory=list)
    dispatch: DispatchConfig = Field(default_factory=DispatchConfig)
    billing: BillingConfig = Field(default_factory=BillingConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    system: SystemConfig = Field(default_factory=SystemConfig)
