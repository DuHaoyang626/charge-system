"""
管理端 — 会话管理路由
"""
from fastapi import APIRouter, Depends, Query

from core.deps import get_current_admin
from core.exceptions import AppException
from core.response import resp_ok
from service.admin.service import list_all_sessions, get_admin_session_detail

router = APIRouter(tags=["管理端-会话"])


@router.get("/admin/sessions")
async def admin_list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    station_id: int | None = Query(None, alias="stationId"),
    user_id: int | None = Query(None, alias="userId"),
    admin_id: int = Depends(get_current_admin),
):
    """查看所有用户会话（分页）。"""
    data = list_all_sessions(
        page=page, page_size=page_size,
        status=status, station_id=station_id, user_id=user_id,
    )
    return resp_ok(data=data)


@router.get("/admin/sessions/{session_id}")
async def admin_get_session(
    session_id: int,
    admin_id: int = Depends(get_current_admin),
):
    """查看任意会话详情。"""
    data = get_admin_session_detail(session_id)
    if data is None:
        from core.exceptions import Err
        raise AppException(*Err.NOT_FOUND)
    return resp_ok(data=data)
