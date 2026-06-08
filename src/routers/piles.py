"""
充电桩管理路由 — /api/piles
覆盖用例：UC-17（控制充电桩可用性）、UC-18（修改参数）、UC-23（运行充电桩）、UC-14（查看状态）
"""

from datetime import datetime

from fastapi import APIRouter

from src.db.database import get_session
from src.db.models import ChargingPile, PileTariffConfig
from src.enums import LogModule
from src.schemas.admin import SetParametersRequest
from src.services.monitor_service import MonitorService
from src.utils.logger import logger

router = APIRouter(prefix="/api/piles", tags=["充电桩管理"])

_monitor = MonitorService()


@router.post("/{pile_id}/power/on", summary="启动充电桩电源", response_model=dict)
def power_on(pile_id: str):
    session = get_session()
    try:
        pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == pile_id
        ).first()
        if not pile:
            return {"success": False, "message": "充电桩不存在"}
        pile.status = "AVAILABLE"
        pile.updated_at = datetime.now()
        session.commit()
        logger.notice(LogModule.ADMIN, f"[管理] powerOn (pile_id: {pile_id})")
        return {"success": True, "message": "充电桩电源已开启"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"操作失败: {e}"}
    finally:
        session.close()


@router.put("/{pile_id}/parameters", summary="设置充电桩参数", response_model=dict)
def set_parameters(pile_id: str, body: SetParametersRequest):
    session = get_session()
    try:
        existing = session.query(PileTariffConfig).filter(
            PileTariffConfig.pile_id == pile_id
        ).first()
        now = datetime.now()
        if existing:
            existing.peak_price = body.peak_price
            existing.normal_price = body.normal_price
            existing.valley_price = body.valley_price
            existing.base_service_fee = body.base_service_fee
            existing.time_coefficient = body.time_coefficient
            existing.updated_at = now
        else:
            session.add(PileTariffConfig(
                pile_id=pile_id,
                peak_price=body.peak_price,
                normal_price=body.normal_price,
                valley_price=body.valley_price,
                base_service_fee=body.base_service_fee,
                time_coefficient=body.time_coefficient,
                created_at=now, updated_at=now,
            ))
        session.commit()
        logger.notice(LogModule.ADMIN,
                      f"[管理] 更新 {pile_id} 计费规则 (peak:{body.peak_price})")
        return {"success": True, "message": "参数设置成功"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"设置失败: {e}"}
    finally:
        session.close()


@router.post("/{pile_id}/run", summary="运行充电桩", response_model=dict)
def start_charging_pile(pile_id: str):
    session = get_session()
    try:
        pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == pile_id
        ).first()
        if not pile:
            return {"success": False, "message": "充电桩不存在"}
        pile.status = "RUNNING"
        pile.updated_at = datetime.now()
        session.commit()
        return {"success": True, "message": "充电桩已进入运行状态"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"操作失败: {e}"}
    finally:
        session.close()


@router.post("/{pile_id}/power/off", summary="关闭充电桩", response_model=dict)
def power_off(pile_id: str):
    session = get_session()
    try:
        pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == pile_id
        ).first()
        if not pile:
            return {"success": False, "message": "充电桩不存在"}
        if pile.current_charging_count > 0:
            return {"success": False, "message": "充电桩正在使用中，无法关机"}
        pile.status = "CLOSED"
        pile.updated_at = datetime.now()
        session.commit()
        return {"success": True, "message": "充电桩已关闭"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"操作失败: {e}"}
    finally:
        session.close()


@router.get("/{pile_id}/state", summary="查看充电桩状态", response_model=dict)
def query_pile_state(pile_id: str):
    stats = _monitor.get_pile_stats(pile_id)
    if "success" in stats and stats.get("success") is False:
        return stats
    return {"success": True, **stats}
