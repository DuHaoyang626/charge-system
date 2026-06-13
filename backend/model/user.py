"""
用户模型 (users)

角色：
    - admin  : 系统管理员，可访问管理端所有 API
    - user   : 普通车主用户
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: int | None = Field(default=None, primary_key=True)
    license_plate: str = Field(unique=True, index=True, max_length=20, description="车牌号 / ADMIN")
    user_name: str = Field(max_length=50, description="用户昵称")
    password: str = Field(max_length=200, description="bcrypt 哈希后的密码")
    phone: str | None = Field(default=None, max_length=20, description="手机号")
    battery_capacity: float = Field(default=0, description="电池容量 (kWh)，管理员为 0")
    role: str = Field(default="user", max_length=10, description="角色: user / admin")
    balance: float = Field(default=0, description="账户余额 (分)")
    priority: int = Field(default=0, description="优先级: 0=普通 1=VIP")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )
