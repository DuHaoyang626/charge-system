"""
充电桩管理路由 — /api/piles
覆盖用例：UC-17（控制充电桩可用性）、UC-18（修改参数）、UC-23（运行充电桩）、UC-14（查看状态）
"""

from datetime import datetime

from fastapi import APIRouter, Depends

from src.db.database import get_session
from src.db.models import ChargingPile, ChargingRequest, PileTariffConfig
from src.enums import LogModule
from src.routers.admin import require_admin
from src.schemas.admin import SetParametersRequest
from src.services.monitor_service import MonitorService
from src.utils.logger import logger

router = APIRouter(prefix="/api/piles", tags=["充电桩管理"])

_monitor = MonitorService()


# ======================================================================
# 充电桩总览（所有桩实时状态，供前端图表展示）
# ======================================================================

@router.get("/overview", summary="所有充电桩实时状态总览", response_model=dict)
def get_piles_overview():
    """获取所有充电桩的实时运行状态总览，供前端图表和监控面板使用。

    **成功响应：**
    ```json
    {
        "success": true,
        "piles": [
            {
                "pile_id": "P001",
                "pile_name": "快充桩-01",
                "type": "fast_charge",
                "max_power_kw": 120.0,
                "status": "CHARGING",
                "current_charging_count": 1,
                "queue_length": 3,
                "waiting_length": 2,
                "total_charge_num": 125,
                "total_charge_time": 4560.5,
                "total_capacity": 8520.0
            }
        ],
        "summary": {
            "total_piles": 5,
            "charging": 2,
            "available": 1,
            "fault": 0,
            "closed": 0,
            "total_charging_now": 2,
            "total_queue_length": 8
        }
    }
    ```
    """
    session = get_session()
    try:
        piles = session.query(ChargingPile).all()
        result = []
        summary = {
            "total_piles": len(piles),
            "charging": 0,
            "available": 0,
            "running": 0,
            "fault": 0,
            "closed": 0,
            "total_charging_now": 0,
            "total_queue_length": 0,
        }

        for pile in piles:
            # 查询排队长队
            queue_count = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile.pile_id,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
            ).count()
            waiting_count = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile.pile_id,
                ChargingRequest.zone_type == "WAITING_AREA",
                ChargingRequest.is_active == 1,
            ).count()

            # 统计
            status_key = pile.status.lower()
            if status_key in summary:
                summary[status_key] += 1
            summary["total_charging_now"] += (pile.current_charging_count or 0)
            summary["total_queue_length"] += queue_count

            result.append({
                "pile_id": pile.pile_id,
                "pile_name": pile.pile_name,
                "type": pile.type,
                "max_power_kw": float(pile.max_power_kw),
                "status": pile.status,
                "current_charging_count": pile.current_charging_count or 0,
                "queue_length": queue_count,
                "waiting_length": waiting_count,
                "total_charge_num": pile.total_charge_num or 0,
                "total_charge_time": float(pile.total_charge_time or 0),
                "total_capacity": float(pile.total_capacity or 0),
            })

        return {"success": True, "piles": result, "summary": summary}

    except Exception as e:
        logger.error(LogModule.MONITOR, f"[总览] 查询充电桩总览失败: {e}")
        return {"success": False, "message": f"查询失败: {e}"}
    finally:
        session.close()


# ======================================================================
# 充电桩控制（需管理员认证）
# ======================================================================

@router.post("/{pile_id}/power/on", summary="启动充电桩电源",
             response_model=dict, dependencies=[Depends(require_admin)])
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


@router.put("/{pile_id}/parameters", summary="设置充电桩参数",
            response_model=dict, dependencies=[Depends(require_admin)])
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


@router.post("/{pile_id}/run", summary="运行充电桩",
             response_model=dict, dependencies=[Depends(require_admin)])
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


@router.post("/{pile_id}/power/off", summary="关闭充电桩",
             response_model=dict, dependencies=[Depends(require_admin)])
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


# ======================================================================
# 充电桩状态查询（公开，供管理员客户端轮询）
# ======================================================================

@router.get("/{pile_id}/state", summary="查看充电桩状态", response_model=dict)
def query_pile_state(pile_id: str):
    stats = _monitor.get_pile_stats(pile_id)
    if "success" in stats and stats.get("success") is False:
        return stats
    return {"success": True, **stats}
