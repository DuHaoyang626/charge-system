"""
认证模块 — Pydantic 请求/响应模型。
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────
# 注册
# ──────────────────────────────────────────────


class RegisterRequest(BaseModel):
    license_plate: str = Field(alias="licensePlate", min_length=2, max_length=20)
    user_name: str = Field(alias="userName", min_length=1, max_length=50)
    battery_capacity: float = Field(alias="batteryCapacity", gt=0)
    password: str = Field(min_length=6)
    confirm_password: str = Field(alias="confirmPassword", min_length=6)
    protocol_ids: list[int] = Field(alias="protocolIds", min_length=1)
    phone: str | None = Field(default=None, max_length=20)

    model_config = ConfigDict(populate_by_name=True)

class RegisterResponse(BaseModel):
    user_id: int = Field(alias="userId")
    license_plate: str = Field(alias="licensePlate")
    user_name: str = Field(alias="userName")
    token: str

    model_config = ConfigDict(populate_by_name=True)

# ──────────────────────────────────────────────
# 登录
# ──────────────────────────────────────────────


class LoginRequest(BaseModel):
    license_plate: str = Field(alias="licensePlate")
    password: str

    model_config = ConfigDict(populate_by_name=True)

class LoginResponse(BaseModel):
    user_id: int = Field(alias="userId")
    license_plate: str = Field(alias="licensePlate")
    user_name: str = Field(alias="userName")
    token: str
    role: str

    model_config = ConfigDict(populate_by_name=True)

# ──────────────────────────────────────────────
# 用户信息
# ──────────────────────────────────────────────


class ProtocolInfo(BaseModel):
    id: int
    name: str
    power_kw: float = Field(alias="powerKw")

    model_config = ConfigDict(populate_by_name=True)

class ActiveSessionInfo(BaseModel):
    session_id: int = Field(alias="sessionId")
    status: str
    station_name: str = Field(alias="stationName")
    progress: int

    model_config = ConfigDict(populate_by_name=True)

class UserMeResponse(BaseModel):
    user_id: int = Field(alias="userId")
    license_plate: str = Field(alias="licensePlate")
    user_name: str = Field(alias="userName")
    phone: str | None
    battery_capacity: float = Field(alias="batteryCapacity")
    protocols: list[ProtocolInfo]
    active_session: Any | None = Field(default=None, alias="activeSession")

    model_config = ConfigDict(populate_by_name=True)
