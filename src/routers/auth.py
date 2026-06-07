"""
用户认证路由 — /api/auth

接口定义参考：docs/系统架构设计文档.md §5.1
"""

from fastapi import APIRouter

from src.schemas.user import LoginRequest, LoginResponse, SimpleResponse
from src.services.account_service import AccountService

router = APIRouter(prefix="/api/auth", tags=["用户认证"])

_svc = AccountService()


@router.post("/login", summary="用户登录", response_model=dict)
def login(body: LoginRequest):
    """login(car_Id, password)

    用户通过车牌号和密码登录系统。

    **请求体示例：**
    ```json
    {
        "car_Id": "京A12345",
        "password": "Abc12345"
    }
    ```

    **成功响应：**
    ```json
    {
        "success": true,
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user_id": "U20260001",
        "user_name": "张三",
        "license_plate": "京A12345",
        "membership_level": 1
    }
    ```
    """
    result = _svc.authenticate(body.car_id, body.password)
    return result
