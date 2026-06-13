"""
充电会话模型 (sessions)

会话流转：queued → waiting → charging → completed / cancelled

区域 (zone) 与状态 (status) 对应关系：
    zone="queue"    status="queued"
    zone="waiting"  status="waiting"
    zone="charging" status="charging"
    zone=null       status="completed" 或 "cancelled"
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from model.user import User
    from model.station import Station
    from model.protocol import Protocol


class ChargingSession(SQLModel, table=True):
    __tablename__ = "sessions"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    station_id: int = Field(foreign_key="stations.id", index=True)
    protocol_id: int | None = Field(default=None, foreign_key="protocols.id", index=True)

    # 状态
    status: str = Field(max_length=20, description="queued / waiting / charging / completed / cancelled")
    zone: str | None = Field(default=None, max_length=20, description="queue / waiting / charging / null")

    # 充电需求
    requested_energy_kwh: float = Field(description="请求充电量 (kWh)")
    charged_energy_kwh: float = Field(default=0, description="已充电量 (kWh)")

    # 调度就绪标记
    advance_ready: bool = Field(default=False, description="是否就绪可进入下一阶段")

    # 排队位置
    queue_position: int | None = Field(default=None, description="排队/等待区中的位置")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow)
    entered_waiting_at: datetime | None = Field(default=None)
    started_charging_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    cancelled_at: datetime | None = Field(default=None)

    # ── Relationship（仅用于序列化，Service 层优先用显式查询） ──
    user: Optional["User"] = Relationship()
    station: Optional["Station"] = Relationship()
    protocol: Optional["Protocol"] = Relationship()
