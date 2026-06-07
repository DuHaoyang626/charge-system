"""
智能充电桩调度计费系统 — Pydantic Schema 定义

分层设计：
- user.py   用户注册/登录
- charging.py  充电请求/会话/队列
- billing.py  账单/详单/支付
- admin.py    充电桩管理/策略
"""

from pydantic import BaseModel


class ApiBaseModel(BaseModel):
    """所有 API Schema 的基类

    populate_by_name=True 允许同时使用 Python 字段名和别名传入请求数据，
    使 API 既兼容文档中的命名规范（如 car_Id），也支持 Python 风格（car_id）。
    """
    model_config = {"populate_by_name": True}


from .user import *
from .charging import *
from .billing import *
from .admin import *

__all__ = ["ApiBaseModel"]
