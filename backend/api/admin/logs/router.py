"""
管理员 — 系统日志查看
"""
from fastapi import APIRouter, Depends, Query

from core.deps import get_current_admin
from core.response import resp_ok
from model.log_record import LogRecord

router = APIRouter(tags=["管理端-日志"])


@router.get("/admin/logs")
async def get_system_logs(
    level: str | None = Query(None, description="筛选等级: INFO / WARNING / ERROR"),
    module: str | None = Query(None, description="筛选模块名"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    admin_id: int = Depends(get_current_admin),
):
    """查看系统日志（分页），按时间倒序。"""
    from sqlmodel import Session, select, func
    from core.database import engine

    with Session(engine) as db:
        query = select(LogRecord)
        if level:
            query = query.where(LogRecord.level == level.upper())
        if module:
            query = query.where(LogRecord.module == module)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total = db.exec(count_query).one()

        # 分页、倒序
        query = query.order_by(LogRecord.created_at.desc())
        query = query.offset(offset).limit(limit)
        rows = db.exec(query).all()

        logs = []
        for r in rows:
            from datetime import timedelta
            bjt = r.created_at + timedelta(hours=8) if r.created_at else None
            logs.append({
                "id": r.id,
                "level": r.level,
                "module": r.module,
                "content": r.content,
                "createdAt": bjt.isoformat() if bjt else None,
            })

        return resp_ok(data={
            "logs": logs,
            "total": total,
        })
