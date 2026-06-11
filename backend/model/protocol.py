"""
充电协议模型 (protocols)

定义不同功率等级的充电协议，充电桩与用户车辆通过协议匹配。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Protocol(SQLModel, table=True):
    __tablename__ = "protocols"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, description="协议名称，如 AC 7kW")
    power_kw: float = Field(description="功率 (kW)")
    is_fallback: bool = Field(default=False, description="是否兜底协议")
    description: str | None = Field(default=None, max_length=200)

    created_at: datetime = Field(default_factory=datetime.utcnow)
