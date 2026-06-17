"""
系统日志模型 (log_records)

记录每条日志的时间、等级、发送模块、日志内容。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class LogRecord(SQLModel, table=True):
    __tablename__ = "log_records"

    id: int | None = Field(default=None, primary_key=True)
    level: str = Field(max_length=10, index=True, description="日志等级: INFO / WARNING / ERROR")
    module: str = Field(max_length=64, index=True, description="发送日志的模块名")
    content: str = Field(max_length=2000, description="日志内容")

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
