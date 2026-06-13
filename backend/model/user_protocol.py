"""
用户协议关联表 (user_protocols)

记录每个用户支持的充电协议列表。
"""

from sqlmodel import Field, SQLModel


class UserProtocol(SQLModel, table=True):
    __tablename__ = "user_protocols"

    user_id: int = Field(foreign_key="users.id", primary_key=True)
    protocol_id: int = Field(foreign_key="protocols.id", primary_key=True)
