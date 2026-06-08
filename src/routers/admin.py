"""
管理员功能路由 — /api/admin

覆盖用例：
- UC-16 移动车辆位置
- UC-20 生成运营报表
"""

from datetime import datetime

from fastapi import APIRouter, Query

from src.db.database import get_session
from src.db.models import BillingRecord, ChargingPile, ChargingRequest, PaymentOrder
from src.enums import LogModule
from src.utils.logger import logger

router = APIRouter(prefix="/api/admin", tags=["管理员"])


# ======================================================================
# UC-16: 移动车辆位置
# ======================================================================

@router.put("/vehicles/{car_id}/move", summary="移动车辆位置", response_model=dict)
def move_vehicle(
    car_id: str,
    target_pile_id: str = Query(..., description="目标充电桩编号"),
    target_zone: str = Query(..., description="目标区域: QUEUE_AREA/WAITING_AREA/CHARGING_AREA"),
    target_position: int = Query(1, description="目标位置序号"),
):
    """moveVehicle(car_id, targetPileId, targetZone, targetPosition)

    管理员将车辆移动到任何未满队列的任何区域的任意位置。

    **查询参数：**
    - `car_id` (路径): 车牌号
    - `target_pile_id` (必填): 目标充电桩编号
    - `target_zone` (必填): 目标区域 QUEUE_AREA / WAITING_AREA / CHARGING_AREA
    - `target_position` (可选): 目标位置序号，默认 1

    **成功响应：**
    ```json
    {"success": true, "car_id": "京A12345", "new_pile_id": "P002",
     "new_zone": "QUEUE_AREA", "new_position": 1, "message": "车辆已移动"}
    ```

    **失败响应：**
    ```json
    {"success": false, "message": "目标区域已满"}
    ```
    """
    if target_zone not in ("QUEUE_AREA", "WAITING_AREA", "CHARGING_AREA"):
        return {"success": False, "message": f"无效区域: {target_zone}"}

    session = get_session()
    try:
        # 校验目标充电桩
        target_pile = session.query(ChargingPile).filter(
            ChargingPile.pile_id == target_pile_id
        ).first()
        if not target_pile:
            return {"success": False, "message": f"充电桩 {target_pile_id} 不存在"}

        # 查找车辆的活跃请求
        request = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if not request:
            return {"success": False, "message": "该车辆无活跃充电请求"}

        # 检查目标区域容量
        zone_count = session.query(ChargingRequest).filter(
            ChargingRequest.pile_id == target_pile_id,
            ChargingRequest.zone_type == target_zone,
            ChargingRequest.is_active == 1,
        ).count()

        max_zone = {
            "QUEUE_AREA": 100,       # 无上限
            "WAITING_AREA": 5,       # 等待区有限
            "CHARGING_AREA": 2,      # 充电区有限
        }
        max_count = max_zone.get(target_zone, 100)
        if zone_count >= max_count:
            return {"success": False, "message": f"{target_zone} 已满"}

        # 记录移动前状态
        old_pile = request.pile_id
        old_zone = request.zone_type
        old_pos = request.queue_position

        # 执行移动
        request.original_pile_id = old_pile
        request.pile_id = target_pile_id
        request.zone_type = target_zone
        request.queue_position = target_position
        request.updated_at = datetime.now()
        session.commit()

        logger.notice(
            LogModule.ADMIN,
            f"[管理] 移动车辆 {car_id}: {old_pile}/{old_zone}(pos:{old_pos}) "
            f"-> {target_pile_id}/{target_zone}(pos:{target_position})",
        )
        return {
            "success": True,
            "car_id": car_id,
            "new_pile_id": target_pile_id,
            "new_zone": target_zone,
            "new_position": target_position,
            "message": "车辆已移动",
        }

    except Exception as e:
        session.rollback()
        logger.error(LogModule.ADMIN, f"[管理] 移动车辆失败: {e}")
        return {"success": False, "message": f"移动失败: {e}"}
    finally:
        session.close()


# ======================================================================
# UC-20: 生成运营报表
# ======================================================================

@router.get("/reports", summary="生成运营报表", response_model=dict)
def generate_report(
    start_date: str = Query("", description="开始日期 YYYY-MM-DD"),
    end_date: str = Query("", description="结束日期 YYYY-MM-DD"),
):
    """生成运营报表

    返回充电量、收入、利用率等关键运营指标。
    支持按日期范围筛选。

    **查询参数：**
    - `start_date` (可选): 开始日期，默认当月第一天
    - `end_date` (可选): 结束日期，默认当天

    **成功响应：**
    ```json
    {
        "success": true,
        "report": {
            "period": {"start": "2026-06-01", "end": "2026-06-08"},
            "summary": {
                "total_charge_capacity_kwh": 8520.0,
                "total_revenue": 58000.0,
                "total_sessions": 125,
                "utilization_rate": 0.45
            },
            "pile_details": [
                {"pile_id": "P001", "charge_num": 125,
                 "total_capacity_kwh": 8520.0, "charge_time_minutes": 4560.5}
            ]
        }
    }
    ```
    """
    session = get_session()
    try:
        # 确定日期范围
        today = datetime.now().date()
        if not start_date:
            start_date = today.replace(day=1).isoformat()
        if not end_date:
            end_date = today.isoformat()

        # 1. 充电桩统计数据
        piles = session.query(ChargingPile).all()
        total_capacity = sum(float(p.total_capacity or 0) for p in piles)
        total_num = sum(p.total_charge_num or 0 for p in piles)
        total_time = sum(float(p.total_charge_time or 0) for p in piles)
        available_hours = len(piles) * 24 * 30  # 估算可用总时长
        utilization = (total_time / (available_hours * 60)) if available_hours > 0 else 0

        # 2. 收入统计
        revenue = session.query(
            BillingRecord
        ).filter(
            BillingRecord.date >= start_date,
            BillingRecord.date <= end_date,
        ).all()
        total_revenue = sum(float(b.total_fee or 0) for b in revenue)

        # 3. 按桩明细
        pile_details = []
        for p in piles:
            pile_details.append({
                "pile_id": p.pile_id,
                "pile_name": p.pile_name,
                "type": p.type,
                "max_power_kw": float(p.max_power_kw),
                "status": p.status,
                "total_charge_num": p.total_charge_num or 0,
                "total_capacity_kwh": float(p.total_capacity or 0),
                "charge_time_minutes": float(p.total_charge_time or 0),
                "current_charging_count": p.current_charging_count or 0,
            })

        logger.info(LogModule.MONITOR,
                    f"[报表] 生成运营报表 ({start_date} ~ {end_date})")

        return {
            "success": True,
            "report": {
                "period": {"start": start_date, "end": end_date},
                "summary": {
                    "total_charge_capacity_kwh": round(total_capacity, 2),
                    "total_revenue": round(total_revenue, 2),
                    "total_sessions": total_num,
                    "utilization_rate": round(utilization, 4),
                },
                "pile_details": pile_details,
            },
        }

    except Exception as e:
        logger.error(LogModule.MONITOR, f"[报表] 生成报表失败: {e}")
        return {"success": False, "message": f"报表生成失败: {e}"}
    finally:
        session.close()
