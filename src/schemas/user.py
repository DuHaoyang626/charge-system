"""
用户注册/登录 — Pydantic Schema
对应 API: /api/accounts, /api/auth
"""

from datetime import datetime

from pydantic import Field

from src.schemas import ApiBaseModel


# ── 请求体 ─────────────────────────────────────────────

class CreateAccountRequest(ApiBaseModel):
    """createNewAccount(car_Id, userName, car_Capacity)"""
    car_id: str = Field(..., description="车牌号", alias="car_Id")
    user_name: str = Field(..., description="用户名", alias="userName")
    car_capacity: float = Field(..., gt=0, description="电池容量(kWh)", alias="car_Capacity")


class SetPasswordRequest(ApiBaseModel):
    """set_pwd(******)"""
    password: str = Field(..., min_length=6, description="密码")


class LoginRequest(ApiBaseModel):
    """login(car_Id, password)"""
    car_id: str = Field(..., description="车牌号", alias="car_Id")
    password: str = Field(..., description="密码")


# ── 响应体 ─────────────────────────────────────────────

class AccountResponse(ApiBaseModel):
    """账号基础信息"""
    user_id: str
    user_name: str
    license_plate: str
    membership_level: int
    account_status: str
    created_at: datetime


class LoginResponse(ApiBaseModel):
    """登录成功返回"""
    access_token: str
    token_type: str = "bearer"
    user: AccountResponse


class SimpleResponse(ApiBaseModel):
    """通用成功/失败响应（Return(0/1)）"""
    success: bool = Field(..., description="操作是否成功")
    message: str = ""
