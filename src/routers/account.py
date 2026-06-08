"""
用户账号管理路由 — /api/accounts

接口定义参考：docs/系统架构设计文档.md §5.1
"""

from fastapi import APIRouter

from src.schemas.user import (AccountResponse, CreateAccountRequest,
                               SetPasswordRequest, SimpleResponse)
from src.services.account_service import AccountService

router = APIRouter(prefix="/api/accounts", tags=["用户账号"])

# 临时实例，后续通过依赖注入
_svc = AccountService()


@router.post("", summary="创建新账号", response_model=dict)
def create_account(body: CreateAccountRequest):
    """createNewAccount(car_Id, userName, car_Capacity)

    新用户注册，创建账号和关联的车辆信息。

    **请求体示例：**
    ```json
    {
        "car_Id": "京A12345",
        "userName": "张三",
        "car_Capacity": 60.0
    }
    ```

    **成功响应：**
    ```json
    {"success": true, "user_id": "U20260001", "message": "账号创建成功"}
    ```
    """
    result = _svc.create_account(body.car_id, body.user_name, body.car_capacity)
    return result


@router.put("/{car_id}/password", summary="设置密码", response_model=dict)
def set_password(car_id: str, body: SetPasswordRequest):
    """set_pwd(******)

    用户设置或修改登录密码。

    **请求体示例：**
    ```json
    {"password": "Abc12345"}
    ```

    **成功响应：**
    ```json
    {"success": true, "message": "密码设置成功"}
    ```
    """
    from src.db.database import get_session
    from src.db.models import User
    session = get_session()
    try:
        user = session.query(User).filter(User.license_plate == car_id).first()
        if not user:
            return {"success": False, "message": "用户不存在"}
        user_id = user.user_id
    finally:
        session.close()
    result = _svc.set_password(user_id, body.password)
    return result
