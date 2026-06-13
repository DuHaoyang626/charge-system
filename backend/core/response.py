"""
统一响应格式工具。

所有接口通过 resp_ok() / resp_err() 返回，无需手动组装 JSON。
"""

import time
from typing import Any

from fastapi.responses import JSONResponse


def resp_ok(
    data: Any = None,
    message: str = "success",
    code: int = 200,
    status_code: int = 200,
) -> JSONResponse:
    """成功响应。"""
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        },
    )


def resp_err(
    code: int = 400,
    message: str = "请求失败",
    data: Any = None,
) -> JSONResponse:
    """错误响应（直接返回，不走异常处理器）。"""
    return JSONResponse(
        status_code=code,
        content={
            "code": code,
            "message": message,
            "data": data,
            "timestamp": int(time.time() * 1000),
        },
    )


def resp_page(
    list_data: list,
    total: int,
    page: int,
    page_size: int,
) -> JSONResponse:
    """分页响应。"""
    return JSONResponse(
        status_code=200,
        content={
            "code": 200,
            "data": {
                "list": list_data,
                "page": page,
                "pageSize": page_size,
                "total": total,
            },
            "message": "success",
            "timestamp": int(time.time() * 1000),
        },
    )
