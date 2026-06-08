"""
队列服务 — QueueService

职责：车辆入队/出队/换队、三区流转、状态查询
三区模型：排队区(QUEUE_AREA) → 等待区(WAITING_AREA) → 充电区(CHARGING_AREA)
"""

from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_

from src.config import config
from src.db.database import get_session
from src.db.models import ChargingPile, ChargingRequest, Vehicle
from src.enums import LogModule
from src.utils.logger import logger


class QueueService:
    """三区队列服务（每个充电桩独立维护一条队列）"""

    # ------------------------------------------------------------------
    # enqueue: 车辆进入指定充电桩的排队区
    # ------------------------------------------------------------------
    def enqueue(self, car_id: str, pile_id: str, charging_mode: str,
                 target_power_kwh: float = 0) -> dict:
        """车辆入队

        将车辆加入指定充电桩的排队区队尾。

        Args:
            car_id: 车牌号
            pile_id: 目标充电桩编号
            charging_mode: 充电模式（FAST_CHARGE / SLOW_CHARGE）
            target_power_kwh: 目标充电量（kWh），用于计算等待时间

        Returns:
            {"success": True, "queue_position": 3, "pile_id": "P001",
             "estimated_wait_minutes": 25.5}
            {"success": False, "message": "排队区已满"}
        """
        session = get_session()
        try:
            # 1. 校验充电桩存在且状态可用
            pile = session.query(ChargingPile).filter(
                ChargingPile.pile_id == pile_id
            ).first()
            if not pile:
                return {"success": False, "message": f"充电桩 {pile_id} 不存在"}
            if pile.status in ("CLOSED", "FAULT"):
                return {
                    "success": False,
                    "message": f"充电桩 {pile_id} 当前状态不可用 ({pile.status})",
                }

            # 2. 检查排队区容量
            current_count = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile_id,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
            ).count()
            max_queue = config.station.max_queue_capacity
            if current_count >= max_queue:
                return {"success": False, "message": "排队区已满"}

            # 3. 创建充电请求记录
            now = datetime.now()
            request_id = f"R{now.strftime('%Y%m%d%H%M%S%f')}"
            queue_position = current_count + 1

            request = ChargingRequest(
                request_id=request_id,
                car_id=car_id,
                pile_id=pile_id,
                request_time=now,
                charging_mode=charging_mode,
                target_power_kwh=target_power_kwh,
                request_status="QUEUED",
                zone_type="QUEUE_AREA",
                queue_position=queue_position,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(request)

            # 4. 计算 estimated_wait_minutes
            # 前方所有活跃请求的目标电量 / 桩最大功率
            ahead_requests = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile_id,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
                ChargingRequest.queue_position < queue_position,
            ).all()
            total_ahead_kwh = sum(
                float(r.target_power_kwh) for r in ahead_requests
            )
            pile_power_kw = float(pile.max_power_kw)
            estimated_wait_minutes = (
                (total_ahead_kwh / pile_power_kw * 60) if pile_power_kw > 0 else 0
            )

            session.commit()

            logger.info(
                LogModule.QUEUE,
                f"[入队] {car_id} 进入 {pile_id} 排队区 (position: {queue_position})",
            )
            return {
                "success": True,
                "queue_position": queue_position,
                "pile_id": pile_id,
                "estimated_wait_minutes": round(estimated_wait_minutes, 1),
            }

        except Exception as e:
            session.rollback()
            logger.error(
                LogModule.QUEUE,
                f"[入队] 入队失败 (car_id: {car_id}, pile_id: {pile_id}, error: {str(e)})",
            )
            return {"success": False, "message": f"入队失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # dequeue: 将排队区最前面的车辆移出（自动进入等待区）
    # ------------------------------------------------------------------
    def dequeue(self, pile_id: str) -> dict:
        """排队区出队（自动进入等待区）

        将指定充电桩排队区最前面的车辆移至该桩的等待区。
        在排队区排到最前时由系统自动调用，无需用户确认。

        Args:
            pile_id: 充电桩编号

        Returns:
            有车可出队: {"success": True, "car_id": "京A12345", "to_zone": "WAITING_AREA",
                         "position_in_waiting": 2}
            排队区为空: {"success": False, "message": "排队区无车辆"}
        """
        session = get_session()
        try:
            # 1. 查找排队区第一辆车
            request = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile_id,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
            ).order_by(ChargingRequest.queue_position.asc()).first()

            if not request:
                return {"success": False, "message": "排队区无车辆"}

            # 2. 检查等待区容量
            current_waiting_count = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile_id,
                ChargingRequest.zone_type == "WAITING_AREA",
                ChargingRequest.is_active == 1,
            ).count()
            max_waiting = config.station.max_waiting_capacity
            if current_waiting_count >= max_waiting:
                return {"success": False, "message": "等待区已满"}

            # 3. 更新到等待区
            now = datetime.now()
            request.zone_type = "WAITING_AREA"
            request.request_status = "WAITING"
            request.queue_position = current_waiting_count + 1
            request.updated_at = now

            session.commit()

            logger.info(
                LogModule.QUEUE,
                f"[流转] {request.car_id} 自动进入 {pile_id} 等待区 "
                f"(position: {request.queue_position})",
            )
            return {
                "success": True,
                "car_id": request.car_id,
                "to_zone": "WAITING_AREA",
                "position_in_waiting": request.queue_position,
            }

        except Exception as e:
            session.rollback()
            logger.error(
                LogModule.QUEUE,
                f"[出队] 出队失败 (pile_id: {pile_id}, error: {str(e)})",
            )
            return {"success": False, "message": f"出队失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # changeQueue: 用户在排队区自由更换到其他充电桩的队列
    # ------------------------------------------------------------------
    def change_queue(self, car_id: str, from_pile: str, to_pile: str) -> dict:
        """更换充电桩队列

        用户在排队区可自由更换到其他充电桩队列。
        更换后排至目标队列队尾，原队列中的位置释放。

        Args:
            car_id: 车牌号
            from_pile: 当前充电桩编号
            to_pile: 目标充电桩编号

        Returns:
            {"success": True, "new_pile_id": "P003", "new_position": 2,
             "estimated_wait_minutes": 30.0}
        """
        session = get_session()
        try:
            # 1. 校验请求存在且处于排队区
            request = session.query(ChargingRequest).filter(
                ChargingRequest.car_id == car_id,
                ChargingRequest.pile_id == from_pile,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
            ).first()
            if not request:
                return {
                    "success": False,
                    "message": f"车辆 {car_id} 不在 {from_pile} 的排队区",
                }

            # 2. 校验目标桩存在
            to_pile_obj = session.query(ChargingPile).filter(
                ChargingPile.pile_id == to_pile
            ).first()
            if not to_pile_obj:
                return {"success": False, "message": f"目标充电桩 {to_pile} 不存在"}

            if to_pile_obj.status in ("CLOSED", "FAULT"):
                return {
                    "success": False,
                    "message": f"目标充电桩 {to_pile} 当前状态不可用 ({to_pile_obj.status})",
                }

            # 3. 检查目标队列容量
            current_to_count = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == to_pile,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
            ).count()
            max_queue = config.station.max_queue_capacity
            if current_to_count >= max_queue:
                return {
                    "success": False,
                    "message": f"目标充电桩 {to_pile} 排队区已满",
                }

            # 4. 更新请求
            now = datetime.now()
            request.original_pile_id = request.pile_id
            request.pile_id = to_pile
            request.queue_position = current_to_count + 1
            request.updated_at = now

            # 5. 计算新队列的等待时间
            ahead_requests = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == to_pile,
                ChargingRequest.zone_type == "QUEUE_AREA",
                ChargingRequest.is_active == 1,
                ChargingRequest.queue_position < request.queue_position,
            ).all()
            total_ahead_kwh = sum(
                float(r.target_power_kwh) for r in ahead_requests
            )
            pile_power_kw = float(to_pile_obj.max_power_kw)
            estimated_wait_minutes = (
                (total_ahead_kwh / pile_power_kw * 60) if pile_power_kw > 0 else 0
            )

            session.commit()

            logger.info(
                LogModule.QUEUE,
                f"[换队] {car_id} 从 {from_pile} 换至 {to_pile} "
                f"(new_position: {request.queue_position})",
            )
            return {
                "success": True,
                "new_pile_id": to_pile,
                "new_position": request.queue_position,
                "estimated_wait_minutes": round(estimated_wait_minutes, 1),
            }

        except Exception as e:
            session.rollback()
            logger.error(
                LogModule.QUEUE,
                f"[换队] 换队失败 (car_id: {car_id}, error: {str(e)})",
            )
            return {"success": False, "message": f"换队失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # getCarState: 查询车辆当前在队列中的状态
    # ------------------------------------------------------------------
    def get_car_state(self, car_id: str) -> dict:
        """查询车辆排队状态

        Args:
            car_id: 车牌号

        Returns:
            {"success": True, "car_state": "QUEUED", "queue_num": "P001",
             "cars_before": 3, "request_time": "2026-06-07T10:30:00",
             "zone_type": "QUEUE_AREA"}
            {"success": False, "message": "无活跃请求"}
        """
        session = get_session()
        try:
            # 1. 查找活跃请求
            request = session.query(ChargingRequest).filter(
                ChargingRequest.car_id == car_id,
                ChargingRequest.is_active == 1,
            ).first()
            if not request:
                return {"success": False, "message": "无活跃请求"}

            # 2. 计算前方车辆数（同桩同区且位置更小）
            cars_before = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == request.pile_id,
                ChargingRequest.zone_type == request.zone_type,
                ChargingRequest.is_active == 1,
                ChargingRequest.queue_position < request.queue_position,
            ).count()

            return {
                "success": True,
                "car_state": request.request_status,
                "queue_num": request.pile_id,
                "cars_before": cars_before,
                "request_time": request.request_time.isoformat(),
                "zone_type": request.zone_type,
            }

        except Exception as e:
            logger.error(
                LogModule.QUEUE,
                f"[状态查询] 查询失败 (car_id: {car_id}, error: {str(e)})",
            )
            return {"success": False, "message": f"查询失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # getQueueDetail: 管理员查看指定队列的详情
    # ------------------------------------------------------------------
    def get_queue_detail(self, pile_ids: list[str]) -> list:
        """查看队列详情（管理员用）

        返回指定充电桩队列中所有车辆的详细信息。

        Args:
            pile_ids: 充电桩编号列表

        Returns:
            [{"pile_id": "P001",
              "vehicles": [
                  {"car_id": "京A12345", "battery_capacity_kwh": 60.0,
                   "request_amount_kwh": 50.0, "wait_minutes": 15.0},
                  ...
              ]},
             ...]
        """
        if not pile_ids:
            return []

        session = get_session()
        try:
            # 查询所有活跃请求（左关联车辆电池容量，车辆可能未注册）
            rows = session.query(ChargingRequest, Vehicle.battery_capacity_kwh).outerjoin(
                Vehicle, ChargingRequest.car_id == Vehicle.license_plate
            ).filter(
                ChargingRequest.pile_id.in_(pile_ids),
                ChargingRequest.is_active == 1,
            ).order_by(
                ChargingRequest.pile_id.asc(),
                ChargingRequest.zone_type.asc(),
                ChargingRequest.queue_position.asc(),
            ).all()

            # 分组：pile_id → vehicles
            pile_vehicles = defaultdict(list)
            for req, battery_capacity in rows:
                bat_cap = float(battery_capacity) if battery_capacity is not None else 0.0
                pile_vehicles[req.pile_id].append({
                    "car_id": req.car_id,
                    "battery_capacity_kwh": bat_cap,
                    "request_amount_kwh": float(req.target_power_kwh),
                    "wait_minutes": 0,  # 下方累计计算
                })

            # 获取充电桩功率信息
            pile_power_map = {}
            if pile_ids:
                piles = session.query(ChargingPile).filter(
                    ChargingPile.pile_id.in_(pile_ids)
                ).all()
                for p in piles:
                    pile_power_map[p.pile_id] = float(p.max_power_kw)

            # 按桩组装结果并计算累计等待时间
            result = []
            for pile_id in pile_ids:
                vehicles = pile_vehicles.get(pile_id, [])
                if not vehicles:
                    continue

                pile_power_kw = pile_power_map.get(pile_id, 0)

                # 计算累计等待分钟数
                cumulative_wait = 0.0
                for i, v in enumerate(vehicles):
                    if i > 0:
                        prev_amount = vehicles[i - 1]["request_amount_kwh"]
                        if pile_power_kw > 0:
                            cumulative_wait += prev_amount / pile_power_kw * 60
                    v["wait_minutes"] = round(cumulative_wait, 1)

                result.append({
                    "pile_id": pile_id,
                    "vehicles": vehicles,
                })

            return result

        except Exception as e:
            logger.error(
                LogModule.QUEUE,
                f"[队列详情] 查询失败 (pile_ids: {pile_ids}, error: {str(e)})",
            )
            return []
        finally:
            session.close()
