"""
全局异常处理器 — 将 AppException 捕获并返回统一 JSON 格式响应。

响应格式：
    {
        "code": 400,
        "message": "具体错误描述",
        "data": null,
        "timestamp": 1700000000000
    }
"""

import time

from fastapi import Request
from fastapi.responses import JSONResponse

from core.exceptions import AppException


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """捕获 AppException 并返回统一格式的错误响应。"""
    return JSONResponse(
        status_code=exc.code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": int(time.time() * 1000),
        },
    )
