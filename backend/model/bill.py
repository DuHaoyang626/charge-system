"""
账单模型 (bills)

每笔充电会话完成后生成一条账单记录。
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from model.user import User
    from model.session import ChargingSession


class Bill(SQLModel, table=True):
    __tablename__ = "bills"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", unique=True, index=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    station_id: int = Field(foreign_key="stations.id")
    station_name: str = Field(max_length=50, default="")
    protocol_name: str = Field(max_length=50, default="")
    power_kw: float = Field(default=0)

    # 电量
    total_energy_kwh: float = Field(default=0)

    # 费用 (元)
    electricity_fee: float = Field(default=0)
    service_fee: float = Field(default=0)
    total_fee: float = Field(default=0)

    # 支付状态
    status: str = Field(default="unpaid", max_length=20, description="unpaid / paid")
    paid_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # ── Relationship（仅用于序列化） ──
    session: Optional["ChargingSession"] = Relationship()
    user: Optional["User"] = Relationship()
