"""
调度日志模型 (schedule_logs)

记录每次调度动作：排队 → 等待区 → 充电区 的三区流转。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class ScheduleLog(SQLModel, table=True):
    __tablename__ = "schedule_logs"

    id: int | None = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="sessions.id", index=True)
    from_station_id: int | None = Field(default=None, foreign_key="stations.id")
    to_station_id: int | None = Field(default=None, foreign_key="stations.id")
    from_zone: str | None = Field(default=None, max_length=20)
    to_zone: str | None = Field(default=None, max_length=20)
    triggered_by: str = Field(default="system", max_length=20, description="system / user / admin")
    detail: str | None = Field(default=None, max_length=500)

    created_at: datetime = Field(default_factory=datetime.utcnow)
