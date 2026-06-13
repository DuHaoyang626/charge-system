"""
认证模块路由 — 注册 / 登录
"""

from fastapi import APIRouter

from api.auth.schema import LoginRequest, RegisterRequest
from core.response import resp_err, resp_ok
from service.account.service import login, register

router = APIRouter(tags=["认证"])


@router.post("/auth/register", status_code=201)
async def api_register(body: RegisterRequest):
    """用户注册。"""
    if body.password != body.confirm_password:
        return resp_err(400, "两次密码输入不一致")

    result = register(
        license_plate=body.license_plate,
        user_name=body.user_name,
        battery_capacity=body.battery_capacity,
        password=body.password,
        protocol_ids=body.protocol_ids,
        phone=body.phone,
    )
    return resp_ok(data=result, message="注册成功", code=201, status_code=201)


@router.post("/auth/login")
async def api_login(body: LoginRequest):
    """用户登录。"""
    result = login(
        license_plate=body.license_plate,
        password=body.password,
    )
    return resp_ok(data=result, message="登录成功")
