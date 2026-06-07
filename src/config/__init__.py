"""
配置管理 — ConfigLoader 和类型安全的 Settings 类

使用方式：
    from src.config import config
    config.load()  # 启动时调用
    config.billing.default_prices.peak_price  # 访问配置项
"""

from src.config.loader import ConfigLoader, config
from src.config.settings import (
    AppSettings,
    StationConfig,
    PileConfig,
    DispatchConfig,
    BillingConfig,
    LoggingConfig,
    SystemConfig,
    TimePeriods,
    TimeRange,
    DefaultPrices,
    ServiceFee,
    TimeoutConfig,
    MonitoringConfig,
)

__all__ = [
    "ConfigLoader",
    "config",
    "AppSettings",
    "StationConfig",
    "PileConfig",
    "DispatchConfig",
    "BillingConfig",
    "LoggingConfig",
    "SystemConfig",
    "TimePeriods",
    "TimeRange",
    "DefaultPrices",
    "ServiceFee",
    "TimeoutConfig",
    "MonitoringConfig",
]
