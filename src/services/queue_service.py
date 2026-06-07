"""
队列服务 — QueueService

职责：车辆入队/出队/换队、三区流转、状态查询
三区模型：排队区(QUEUE_AREA) → 等待区(WAITING_AREA) → 充电区(CHARGING_AREA)
"""

from typing import Optional


class QueueService:
    """三区队列服务（每个充电桩独立维护一条队列）"""

    # ------------------------------------------------------------------
    # enqueue: 车辆进入指定充电桩的排队区
    # ------------------------------------------------------------------
    def enqueue(self, car_id: str, pile_id: str, charging_mode: str) -> dict:
        """车辆入队

        将车辆加入指定充电桩的排队区队尾。

        Args:
            car_id: 车牌号
            pile_id: 目标充电桩编号
            charging_mode: 充电模式（FAST_CHARGE / SLOW_CHARGE）

        Returns:
            {"success": True, "queue_position": 3, "pile_id": "P001",
             "estimated_wait_minutes": 25.5}
            {"success": False, "message": "排队区已满"}

        Examples:
            >>> qs = QueueService()
            >>> qs.enqueue("京A12345", "P001", "FAST_CHARGE")
            {"success": True, "queue_position": 3, "pile_id": "P001",
             "estimated_wait_minutes": 25.5}
        """
        # TODO: 真实实现
        # 1. 校验充电桩存在且状态可用 / 运行中
        # 2. 检查排队区容量（SELECT COUNT(*) FROM charging_requests WHERE pile_id=? AND zone_type='QUEUE_AREA' AND is_active=1）
        # 3. 若排队区已满 → return {"success": False, "message": "排队区已满"}
        # 4. INSERT INTO charging_requests (request_id, car_id, pile_id, request_time, charging_mode, ...)
        # 5. 计算排队区人数作为 queue_position
        # 6. logger.info("QUEUE", f"[入队] {car_id} 进入 {pile_id} 排队区 (position: {pos})")
        # 7. return {"success": True, "queue_position": pos, "pile_id": pile_id,
        #            "estimated_wait_minutes": 等待时间估算}
        return {
            "success": True,
            "queue_position": 3,
            "pile_id": pile_id,
            "estimated_wait_minutes": 25.5,
        }

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

        Examples:
            >>> qs.dequeue("P001")
            {"success": True, "car_id": "京A12345", "to_zone": "WAITING_AREA",
             "position_in_waiting": 2}
        """
        # TODO: 真实实现
        # 1. SELECT * FROM charging_requests WHERE pile_id=? AND zone_type='QUEUE_AREA' AND is_active=1
        #    ORDER BY queue_position ASC LIMIT 1
        # 2. 更新 zone_type='WAITING_AREA', request_status='WAITING'
        # 3. 检查等待区容量
        # 4. 计算等待区位置
        # 5. logger.info("QUEUE", f"[流转] {car_id} 自动进入 {pile_id} 等待区")
        # 6. return {"success": True, ...}
        return {
            "success": True,
            "car_id": "京A12345",
            "to_zone": "WAITING_AREA",
            "position_in_waiting": 2,
        }

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

        Examples:
            >>> qs.change_queue("京A12345", "P001", "P003")
            {"success": True, "new_pile_id": "P003", "new_position": 2,
             "estimated_wait_minutes": 30.0}
        """
        # TODO: 真实实现
        # 1. 校验请求存在且 zone_type='QUEUE_AREA'
        # 2. 校验目标桩兼容性（协议、模式）
        # 3. 更新 charging_requests SET pile_id=to_pile, original_pile_id=from_pile
        # 4. 重新计算 queue_position（排到目标队尾）
        # 5. logger.info("QUEUE", f"[换队] {car_id} 从 {from_pile} 换至 {to_pile}")
        # 6. return {"success": True, ...}
        return {
            "success": True,
            "new_pile_id": to_pile,
            "new_position": 2,
            "estimated_wait_minutes": 30.0,
        }

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

        Examples:
            >>> qs.get_car_state("京A12345")
            {"success": True, "car_state": "QUEUED", "queue_num": "P001",
             "cars_before": 3, "request_time": "2026-06-07T10:30:00",
             "zone_type": "QUEUE_AREA"}
        """
        # TODO: 真实实现
        # 1. SELECT * FROM charging_requests WHERE car_id=? AND is_active=1
        # 2. 计算前面排队人数
        # 3. return {"success": True, ...}
        return {
            "success": True,
            "car_state": "QUEUED",
            "queue_num": "P001",
            "cars_before": 3,
            "request_time": "2026-06-07T10:30:00",
            "zone_type": "QUEUE_AREA",
        }

    # ------------------------------------------------------------------
    # getQueueDetail: 管理员查看指定队列的详情
    # ------------------------------------------------------------------
    def get_queue_detail(self, pile_ids: list[str]) -> list:
        """查看队列详情（管理员用）

        返回指定充电桩队列中所有车辆的详细信息。

        Args:
            pile_ids: 充电桩编号列表

        Returns:
            [{"pile_id": "P001", "zone_type": "QUEUE_AREA",
              "vehicles": [
                  {"car_id": "京A12345", "battery_capacity_kwh": 60.0,
                   "request_amount_kwh": 50.0, "wait_minutes": 15.0},
                  ...
              ]},
             ...]

        Examples:
            >>> qs.get_queue_detail(["P001", "P002"])
            [{"pile_id": "P001", ...}, ...]
        """
        # TODO: 真实实现
        # 1. SELECT cr.*, v.battery_capacity_kwh FROM charging_requests cr
        #    JOIN vehicles v ON cr.car_id = v.license_plate
        #    WHERE cr.pile_id IN (?) AND cr.is_active=1 ORDER BY pile_id, queue_position
        # 2. 计算 wait_minutes = NOW - request_time
        # 3. return list
        return [
            {
                "pile_id": pile_ids[0] if pile_ids else "P001",
                "zone_type": "QUEUE_AREA",
                "vehicles": [
                    {
                        "car_id": "京A12345",
                        "battery_capacity_kwh": 60.0,
                        "request_amount_kwh": 50.0,
                        "wait_minutes": 15.0,
                    },
                    {
                        "car_id": "京B67890",
                        "battery_capacity_kwh": 80.0,
                        "request_amount_kwh": 30.0,
                        "wait_minutes": 8.0,
                    },
                ],
            }
        ]
