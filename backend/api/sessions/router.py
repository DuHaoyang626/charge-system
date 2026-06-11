"""
充电会话模块路由占位
"""

from fastapi import APIRouter

router = APIRouter(tags=["充电会话"])


@router.post("/sessions")
async def create_session():
    """发起充电请求（待实现）"""
    return {"message": "create_session - 待实现"}


@router.get("/sessions")
async def list_sessions():
    """充电会话列表（待实现）"""
    return {"message": "list_sessions - 待实现"}


@router.get("/sessions/{session_id}")
async def get_session(session_id: int):
    """充电会话详情（待实现）"""
    return {"message": f"get_session {session_id} - 待实现"}


@router.put("/sessions/{session_id}/energy")
async def update_energy(session_id: int):
    """修改目标电量（待实现）"""
    return {"message": f"update_energy {session_id} - 待实现"}


@router.post("/sessions/{session_id}/cancel")
async def cancel_session(session_id: int):
    """取消充电请求（待实现）"""
    return {"message": f"cancel_session {session_id} - 待实现"}


@router.post("/sessions/{session_id}/stop")
async def stop_charging(session_id: int):
    """停止充电（待实现）"""
    return {"message": f"stop_charging {session_id} - 待实现"}
