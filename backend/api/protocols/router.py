"""
充电协议路由 — 查询可用协议列表
"""

from fastapi import APIRouter

from sqlmodel import Session, select

from core.database import engine
from core.response import resp_ok
from model.protocol import Protocol

router = APIRouter(tags=["协议"])


@router.get("/protocols")
async def list_protocols():
    """获取所有充电协议列表。"""
    with Session(engine) as db:
        protocols = db.exec(select(Protocol).order_by(Protocol.id)).all()
        data = [
            {
                "id": p.id,
                "name": p.name,
                "powerKw": p.power_kw,
            }
            for p in protocols
        ]
        return resp_ok(data=data)
