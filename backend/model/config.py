"""
业务运行时配置模型

分层设计：
    - GlobalConfig       : 键值对配置（如调度算法、基础服务费）
    - ElectricityPrice   : 电价时段表（峰/平/谷）
    - ServiceFeeTier     : 服务费阶梯费率
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class GlobalConfig(SQLModel, table=True):
    __tablename__ = "global_configs"

    id: int | None = Field(default=None, primary_key=True)
    config_key: str = Field(unique=True, max_length=100)
    config_value: str = Field(max_length=500, description="JSON 字符串或纯文本值")
    description: str | None = Field(default=None, max_length=200)
    updated_at: datetime | None = Field(default=None)


class ElectricityPrice(SQLModel, table=True):
    __tablename__ = "electricity_prices"

    id: int | None = Field(default=None, primary_key=True)
    period_name: str = Field(max_length=20, description="时段名称，如峰时/平时/谷时")
    start_time: str = Field(max_length=5, description="开始时间 HH:mm")
    end_time: str = Field(max_length=5, description="结束时间 HH:mm")
    price_per_kwh: float = Field(description="电价 (元/kWh)")
    priority: int = Field(default=0, description="优先级，数字越小越优先匹配")


class ServiceFeeTier(SQLModel, table=True):
    __tablename__ = "service_fee_tiers"

    id: int | None = Field(default=None, primary_key=True)
    tier_name: str | None = Field(default=None, max_length=50)
    min_minutes: int = Field(description="最小分钟数（含）")
    max_minutes: int | None = Field(default=None, description="最大分钟数（不含），null 表示无上限")
    rate_per_minute: float = Field(description="每分钟费率 (元)")
