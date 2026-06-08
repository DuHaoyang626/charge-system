"""
充电流程路由 — /api/charging
"""

from datetime import datetime

from fastapi import APIRouter, Query
from typing import Optional

from src.schemas.charging import (ChargingRequestRequest,
                                   ModifyAmountRequest, ModifyModeRequest,
                                   StartChargingRequest)
from src.db.database import get_session
from src.db.models import ChargingPile, ChargingRequest, ChargingSession, Vehicle
from src.enums import LogModule
from src.services.dispatch_service import DispatchService
from src.services.queue_service import QueueService
from src.utils.logger import logger

router = APIRouter(prefix="/api/charging", tags=["充电流程"])

_dispatch = DispatchService()
_queue = QueueService()


@router.post("/requests", summary="提交充电申请", response_model=dict)
def create_charging_request(body: ChargingRequestRequest):
    """E_chargingRequest(car_Id, Request_Amount, Request_Mode)"""
    result = _dispatch.assign_charging_pile(
        body.car_id, body.request_amount, body.request_mode,
    )
    if not result["success"]:
        return result
    return {
        "success": True,
        "car_position": result.get("queue_position", 1),
        "car_state": "QUEUED",
        "queue_Num": result.get("pile_id", ""),
        "request_time": datetime.now().isoformat(),
    }


@router.put("/requests/{car_id}/amount", summary="修改充电电量", response_model=dict)
def modify_amount(car_id: str, body: ModifyAmountRequest):
    """Modify_Amount(car_Id, Amount)"""
    session = get_session()
    try:
        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if not req:
            return {"success": False, "message": "无活跃充电请求"}
        req.target_power_kwh = body.amount
        req.updated_at = datetime.now()
        session.commit()
        logger.info(LogModule.QUEUE, f"[修改] {car_id} 充电量更新为 {body.amount}kWh")
        return {"success": True, "message": "充电量已更新"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"更新失败: {e}"}
    finally:
        session.close()


@router.put("/requests/{car_id}/mode", summary="修改充电模式", response_model=dict)
def modify_mode(car_id: str, body: ModifyModeRequest):
    """Modify_Mode(car_Id, Mode)"""
    session = get_session()
    try:
        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if not req:
            return {"success": False, "message": "无活跃充电请求"}
        req.charging_mode = body.mode
        req.updated_at = datetime.now()
        session.commit()
        logger.info(LogModule.QUEUE, f"[修改] {car_id} 充电模式更新为 {body.mode}")
        return {"success": True, "message": "充电模式已更新"}
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"更新失败: {e}"}
    finally:
        session.close()


@router.get("/requests/{car_id}/state", summary="查询排队状态", response_model=dict)
def query_car_state(car_id: str):
    """Query_Car_State(car_id)"""
    result = _queue.get_car_state(car_id)
    return {
        "success": result["success"],
        "car_Number_before_position": result.get("cars_before", 0),
        "car_state": result.get("car_state", ""),
        "queue_Num": result.get("queue_num", ""),
        "request_time": result.get("request_time", ""),
    }


@router.post("/sessions", summary="开始充电", response_model=dict)
def start_charging(body: StartChargingRequest):
    """Start_Charging(car_id, ChargePileNum)"""
    session = get_session()
    try:
        pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == body.charge_pile_num
        ).first()
        if not pile:
            return {"success": False, "message": "充电桩不存在"}
        if pile.status not in ("RUNNING", "AVAILABLE"):
            return {"success": False, "message": "充电桩当前状态不可用"}

        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == body.car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if not req:
            return {"success": False, "message": "无活跃充电请求"}

        now = datetime.now()
        session_id = f"S{now.strftime('%Y%m%d%H%M%S%f')}"
        cs = ChargingSession(
            session_id=session_id,
            request_id=req.request_id,
            car_id=body.car_id,
            pile_id=body.charge_pile_num,
            start_time=now,
            target_power_kwh=float(req.target_power_kwh),
            charged_power_kwh=0,
            current_power_kw=float(pile.max_power_kw),
            charging_protocol="GB_STANDARD",
            session_status="ACTIVE",
            created_at=now, updated_at=now,
        )
        session.add(cs)

        req.zone_type = "CHARGING_AREA"
        req.request_status = "CHARGING"
        req.updated_at = now

        pile.status = "CHARGING"
        pile.current_charging_count += 1
        pile.updated_at = now

        session.commit()
        logger.info(LogModule.QUEUE,
                    f"[充电] {body.car_id} 在 {body.charge_pile_num} 开始充电")
        return {"success": True, "session_id": session_id, "message": "开始充电"}

    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"开始充电失败: {e}"}
    finally:
        session.close()


@router.get("/sessions/{car_id}", summary="查询充电状态", response_model=dict)
def query_charging_state(car_id: str):
    """Query_Charging_State(car_id)"""
    from src.config import config

    session = get_session()
    try:
        cs = session.query(ChargingSession).filter(
            ChargingSession.car_id == car_id,
            ChargingSession.session_status == "ACTIVE",
        ).order_by(ChargingSession.start_time.desc()).first()

        if not cs:
            cs = session.query(ChargingSession).filter(
                ChargingSession.car_id == car_id,
            ).order_by(ChargingSession.start_time.desc()).first()

        if not cs:
            return {"success": False, "message": "无充电记录"}

        power_kw = float(cs.current_power_kw) if cs.current_power_kw else 50.0

        if cs.session_status == "ACTIVE":
            now = datetime.now()
            elapsed_hours = max((now - cs.start_time).total_seconds() / 3600.0, 0)
            simulated_kwh = min(elapsed_hours * power_kw, float(cs.target_power_kwh))
            remaining_kwh = float(cs.target_power_kwh) - simulated_kwh
            remaining_min = (remaining_kwh / power_kw * 60) if power_kw > 0 else 0

            peak_price = config.billing.default_prices.peak_price
            base_fee = config.billing.service_fee.base_fee
            coeff = config.billing.service_fee.time_coefficient
            elapsed_min = elapsed_hours * 60
            charge_fee = simulated_kwh * peak_price
            service_fee = base_fee + coeff * elapsed_min

            vehicle = session.query(Vehicle).filter(
                Vehicle.license_plate == car_id
            ).first()
            cap = float(vehicle.battery_capacity_kwh) if vehicle else 60.0
            battery_pct = min(simulated_kwh / cap * 100, 100)

            return {
                "success": True, "car_id": car_id,
                "pile_id": cs.pile_id, "session_id": cs.session_id,
                "current_battery_percentage": round(battery_pct, 1),
                "charged_power_kwh": round(simulated_kwh, 2),
                "current_power_kw": power_kw,
                "estimated_remaining_minutes": round(remaining_min, 1),
                "current_period_price": peak_price,
                "accumulated_fee": round(charge_fee + service_fee, 2),
                "start_time": cs.start_time.isoformat(),
            }

        return {
            "success": True, "car_id": car_id,
            "pile_id": cs.pile_id, "session_id": cs.session_id,
            "charged_power_kwh": float(cs.charged_power_kwh),
            "current_power_kw": power_kw,
            "session_status": cs.session_status,
            "start_time": cs.start_time.isoformat(),
            "end_time": cs.end_time.isoformat() if cs.end_time else None,
        }

    except Exception as e:
        return {"success": False, "message": f"查询失败: {e}"}
    finally:
        session.close()


@router.delete("/sessions/{car_id}", summary="结束充电", response_model=dict)
def end_charging(
    car_id: str,
    charging_pile_num: str = Query(None, alias="ChargingPileNum"),
):
    """End_Charging(car_id, ChargingPileNum)"""
    session = get_session()
    try:
        cs = session.query(ChargingSession).filter(
            ChargingSession.car_id == car_id,
            ChargingSession.session_status == "ACTIVE",
        ).first()
        if not cs:
            return {"success": False, "message": "无活跃充电会话"}

        now = datetime.now()
        cs.end_time = now
        cs.session_status = "COMPLETED"
        cs.updated_at = now

        pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == cs.pile_id
        ).first()
        if pile:
            charged = float(cs.charged_power_kwh) or float(cs.target_power_kwh)
            elapsed_min = max((now - cs.start_time).total_seconds() / 60.0, 0)
            pile.total_charge_num = int(pile.total_charge_num or 0) + 1
            pile.total_charge_time = float(pile.total_charge_time or 0) + elapsed_min
            pile.total_capacity = float(pile.total_capacity or 0) + charged
            pile.current_charging_count = max(pile.current_charging_count - 1, 0)
            pile.status = "RUNNING"
            pile.updated_at = now

        req = session.query(ChargingRequest).filter(
            ChargingRequest.request_id == cs.request_id
        ).first()
        if req:
            req.request_status = "COMPLETED"
            req.is_active = False
            req.updated_at = now

        session.commit()

        from src.services.billing_service import BillingService
        bill = BillingService().calculate_bill(cs.session_id)

        logger.info(LogModule.QUEUE,
                    f"[结束] {car_id} 充电结束, 账单: {bill.get('bill_id', 'N/A')}")
        return {
            "success": True,
            "bill_id": bill.get("bill_id", ""),
            "total_fee": bill.get("total_fee", 0),
            "message": "充电结束",
        }

    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"结束充电失败: {e}"}
    finally:
        session.close()
