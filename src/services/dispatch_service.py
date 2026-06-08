"""
调度服务 — DispatchService

职责：
- 按当前激活策略为充电请求分配最佳充电桩
- 充电桩故障时按五种策略执行重新调度
"""

from datetime import datetime

from src.db.database import get_session
from src.db.models import ChargingPile, ChargingRequest, ChargingSession
from src.enums import LogModule
from src.services.queue_service import QueueService
from src.utils.logger import logger


class DispatchService:
    """充电调度服务"""

    # ==================================================================
    # 内部工具方法
    # ==================================================================

    @staticmethod
    def _get_compatible_piles(charge_mode: str, session) -> list:
        """获取与充电模式兼容且状态可用的充电桩

        Args:
            charge_mode: FAST_CHARGE / SLOW_CHARGE
            session: DB 会话

        Returns:
            list[ChargingPile]: 兼容充电桩列表
        """
        pile_type = "fast_charge" if charge_mode == "FAST_CHARGE" else "slow_charge"

        piles = session.query(ChargingPile).filter(
            ChargingPile.type == pile_type,
            ChargingPile.status.in_(["RUNNING", "AVAILABLE"]),
        ).all()

        return piles

    @staticmethod
    def _get_wait_minutes_for_pile(pile_id: str, pile_power_kw: float,
                                   session) -> float:
        """计算充电桩当前未充电请求（QUEUED/WAITING）的总等待时间（分钟）

        w_i = SUM(target_power_kwh for active QUEUED/WAITING)
              / max_power_kw * 60
        """
        total_kwh = 0.0
        active_requests = session.query(ChargingRequest).filter(
            ChargingRequest.pile_id == pile_id,
            ChargingRequest.is_active == 1,
            ChargingRequest.request_status.in_(["QUEUED", "WAITING"]),
        ).all()
        for r in active_requests:
            total_kwh += float(r.target_power_kwh)

        if pile_power_kw > 0:
            return (total_kwh / pile_power_kw) * 60.0
        return 0.0

    @staticmethod
    def _get_vehicle_charge_mode(car_id: str, vehicle_dict: dict,
                                 session) -> str:
        """获取车辆充电模式，优先级：dict > DB charging_request > DB charging_session"""
        # 1. 从传入 dict 中获取
        mode = vehicle_dict.get("charging_mode", "")
        if not mode:
            mode = vehicle_dict.get("type", "")
        if mode in ("FAST_CHARGE", "fast_charge"):
            return "FAST_CHARGE"
        if mode in ("SLOW_CHARGE", "slow_charge"):
            return "SLOW_CHARGE"

        # 2. 从 DB 活跃充电请求中获取
        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if req:
            return req.charging_mode

        # 3. 从最后一次充电会话推断
        sess = session.query(ChargingSession).filter(
            ChargingSession.car_id == car_id,
        ).order_by(ChargingSession.start_time.desc()).first()
        if sess:
            pile = session.query(ChargingPile).filter(
                ChargingPile.pile_id == sess.pile_id,
            ).first()
            if pile:
                return "FAST_CHARGE" if pile.type == "fast_charge" else "SLOW_CHARGE"

        return ""

    @staticmethod
    def _get_vehicle_request_amount(car_id: str, vehicle_dict: dict,
                                    session) -> float:
        """获取车辆请求电量（kWh），优先级：dict > DB charging_request > 默认 50.0"""
        amount = vehicle_dict.get("request_amount")
        if amount is None:
            amount = vehicle_dict.get("target_power_kwh", 0)
        if float(amount) > 0:
            return float(amount)

        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if req and float(req.target_power_kwh) > 0:
            return float(req.target_power_kwh)

        return 50.0

    def _find_best_pile(self, car_id: str, request_amount: float,
                        charge_mode: str, session) -> tuple:
        """在兼容桩中选择总时间（等待+充电）最短的桩

        T_i = w_i + c_i = 等待分钟数 + 充电分钟数

        Returns:
            (pile_id: str | None, estimated_minutes: float | None)
        """
        compatible = self._get_compatible_piles(charge_mode, session)
        if not compatible:
            return None, None

        best_pile_id = None
        best_time = float('inf')

        for pile in compatible:
            power = float(pile.max_power_kw)
            if power <= 0:
                continue
            w = self._get_wait_minutes_for_pile(pile.pile_id, power, session)
            c = (request_amount / power) * 60.0
            t = w + c

            if t < best_time or (t == best_time and
                                 (best_pile_id is None or
                                  pile.pile_id < best_pile_id)):
                best_time = t
                best_pile_id = pile.pile_id

        return best_pile_id, best_time

    @staticmethod
    def _update_request_pile(car_id: str, new_pile_id: str, session):
        """更新车辆的充电请求中的充电桩编号（如存在活跃请求）"""
        req = session.query(ChargingRequest).filter(
            ChargingRequest.car_id == car_id,
            ChargingRequest.is_active == 1,
        ).first()
        if req:
            req.original_pile_id = req.pile_id
            req.pile_id = new_pile_id
            req.updated_at = datetime.now()
            session.commit()

    def _try_assign(self, vehicle: dict, session) -> dict:
        """尝试将一辆车分配到一个可用充电桩

        Returns:
            {"car_id": ..., "assigned_pile": ..., "success": True/False,
             "estimated_minutes": ...}
        """
        car_id = vehicle.get("car_id", "")
        charge_mode = self._get_vehicle_charge_mode(car_id, vehicle, session)
        amount = self._get_vehicle_request_amount(car_id, vehicle, session)

        # 构建尝试顺序：已知模式优先，再尝试两种模式
        modes_to_try = []
        if charge_mode:
            modes_to_try.append(charge_mode)
        for m in ("FAST_CHARGE", "SLOW_CHARGE"):
            if m not in modes_to_try:
                modes_to_try.append(m)

        for mode in modes_to_try:
            pile_id, minutes = self._find_best_pile(car_id, amount, mode, session)
            if pile_id:
                self._update_request_pile(car_id, pile_id, session)
                return {
                    "car_id": car_id,
                    "assigned_pile": pile_id,
                    "estimated_minutes": round(minutes, 1),
                    "success": True,
                }

        return {"car_id": car_id, "assigned_pile": "", "success": False}

    # ==================================================================
    # assignChargingPile: 为充电请求分配最佳充电桩（E_chargingRequest）
    # ==================================================================

    def assign_charging_pile(self, car_id: str, request_amount: float,
                             request_mode: str) -> dict:
        """分配充电桩 —— SHORTEST_TOTAL_TIME 贪心算法

        T_i = w_i(排队) + c_i(充电)
           w_i = 当前总排队电量/功率*60
           c_i = 请求电量/功率*60
        选择 min(T_i) 的充电桩，平局取 pile_id 更小的。
        """
        session = get_session()
        try:
            compatible = self._get_compatible_piles(request_mode, session)
            if not compatible:
                logger.info(LogModule.DISPATCH,
                            f"[分配] {car_id} 无兼容充电桩可用")
                return {"success": False, "message": "无兼容充电桩可用"}

            best_pile = None
            best_time = float('inf')

            for pile in compatible:
                power = float(pile.max_power_kw)
                if power <= 0:
                    continue
                w = self._get_wait_minutes_for_pile(pile.pile_id, power, session)
                c = (request_amount / power) * 60.0
                t = w + c

                if t < best_time or (t == best_time and
                                     (best_pile is None or
                                      pile.pile_id < best_pile.pile_id)):
                    best_time = t
                    best_pile = pile

            if best_pile is None:
                return {"success": False, "message": "无兼容充电桩可用"}

            # 调用 QueueService 入队
            enq_result = QueueService().enqueue(
                car_id, best_pile.pile_id, request_mode,
                target_power_kwh=request_amount,
            )
            if not enq_result["success"]:
                return enq_result

            logger.info(
                LogModule.DISPATCH,
                f"[分配] {car_id} 分配至 {best_pile.pile_id} "
                f"(T={best_time:.2f}min)",
            )

            return {
                "success": True,
                "pile_id": best_pile.pile_id,
                "estimated_total_minutes": round(best_time, 1),
                "queue_position": enq_result["queue_position"],
                "pile_type": best_pile.type,
            }

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[分配] 分配失败: {str(e)}")
            return {"success": False, "message": f"分配失败: {str(e)}"}
        finally:
            session.close()

    # ==================================================================
    # 故障调度 — 五种策略
    # ==================================================================

    def reschedule_by_priority(self, vehicles: list) -> list:
        """优先级调度（SSD-F1）

        排序：充电中 > 等待区 > 排队区；
        同区域按会员等级降序、等待时间降序。
        """
        session = get_session()
        try:
            zone_priority = {
                "CHARGING_AREA": 0,
                "WAITING_AREA": 1,
                "QUEUE_AREA": 2,
            }

            sorted_vehicles = sorted(
                vehicles,
                key=lambda v: (
                    zone_priority.get(v.get("zone_type", "QUEUE_AREA"), 2),
                    -v.get("membership_level", 0),
                    -v.get("wait_time", 0),
                ),
            )

            results = []
            for vehicle in sorted_vehicles:
                result = self._try_assign(vehicle, session)
                results.append(result)
                car_id = vehicle.get("car_id", "")
                if result["success"]:
                    logger.info(
                        LogModule.DISPATCH,
                        f"[优先级调度] {car_id} -> {result['assigned_pile']}",
                    )
                else:
                    logger.warn(
                        LogModule.DISPATCH,
                        f"[优先级调度] {car_id} 无可用桩",
                    )

            return results

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[优先级调度] 失败: {str(e)}")
            return []
        finally:
            session.close()

    def reschedule_by_time_order(self, vehicles: list) -> list:
        """时间顺序调度（SSD-F2）

        按 request_time 先来后到排序，依次分配可用桩。
        """
        session = get_session()
        try:
            sorted_vehicles = sorted(
                vehicles,
                key=lambda v: v.get("request_time", ""),
            )

            results = []
            for vehicle in sorted_vehicles:
                result = self._try_assign(vehicle, session)
                results.append(result)
                car_id = vehicle.get("car_id", "")
                if result["success"]:
                    logger.info(
                        LogModule.DISPATCH,
                        f"[时间顺序调度] {car_id} -> {result['assigned_pile']}",
                    )
                else:
                    logger.warn(
                        LogModule.DISPATCH,
                        f"[时间顺序调度] {car_id} 无可用桩",
                    )

            return results

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[时间顺序调度] 失败: {str(e)}")
            return []
        finally:
            session.close()

    def recover_charging_fault(self, pile_id: str) -> dict:
        """充电中故障恢复（SSD-F3）

        1. 充电中车辆 -> 优先恢复至同类型可用桩（recovered_count）
        2. 排队/等待车辆 -> 按时间顺序重新调度（rescheduled_count）
        3. 无法分配的无桩可用（pending_count）
        """
        session = get_session()
        try:
            # 获取故障桩的类型
            fault_pile = session.query(ChargingPile).filter(
                ChargingPile.pile_id == pile_id,
            ).first()
            if not fault_pile:
                return {"success": False, "message": f"充电桩 {pile_id} 不存在"}

            charge_mode = ("FAST_CHARGE" if fault_pile.type == "fast_charge"
                           else "SLOW_CHARGE")

            recovered_count = 0
            rescheduled_count = 0
            pending_count = 0

            # 查找所有活跃充电请求（按 request_time 升序）
            requests = session.query(ChargingRequest).filter(
                ChargingRequest.pile_id == pile_id,
                ChargingRequest.is_active == 1,
            ).order_by(ChargingRequest.request_time.asc()).all()

            # 查找活跃充电会话
            active_sessions = session.query(ChargingSession).filter(
                ChargingSession.pile_id == pile_id,
                ChargingSession.session_status == "ACTIVE",
            ).all()

            processed = set()

            # 处理充电中会话
            for sess in active_sessions:
                if sess.car_id in processed:
                    continue
                processed.add(sess.car_id)

                alt_id, _ = self._find_best_pile(
                    sess.car_id, float(sess.target_power_kwh),
                    charge_mode, session,
                )
                if alt_id:
                    self._update_request_pile(sess.car_id, alt_id, session)
                    recovered_count += 1
                else:
                    pending_count += 1

            # 处理请求区车辆
            for req in requests:
                if req.car_id in processed:
                    continue
                processed.add(req.car_id)

                req_charge_mode = req.charging_mode or charge_mode

                if req.zone_type == "CHARGING_AREA":
                    alt_id, _ = self._find_best_pile(
                        req.car_id, float(req.target_power_kwh),
                        req_charge_mode, session,
                    )
                    if alt_id:
                        self._update_request_pile(req.car_id, alt_id, session)
                        recovered_count += 1
                    else:
                        pending_count += 1
                else:
                    alt_id, _ = self._find_best_pile(
                        req.car_id, float(req.target_power_kwh),
                        req_charge_mode, session,
                    )
                    if alt_id:
                        self._update_request_pile(req.car_id, alt_id, session)
                        rescheduled_count += 1
                    else:
                        pending_count += 1

            logger.info(
                LogModule.DISPATCH,
                f"[故障恢复] 桩 {pile_id}: recovered={recovered_count}, "
                f"rescheduled={rescheduled_count}, pending={pending_count}",
            )

            return {
                "success": True,
                "recovered_count": recovered_count,
                "rescheduled_count": rescheduled_count,
                "pending_count": pending_count,
            }

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[故障恢复] 失败: {str(e)}")
            return {"success": False, "message": str(e)}
        finally:
            session.close()

    def reschedule_by_shortest_total_time(self, vehicles: list) -> list:
        """单次调度最短时长（SSD-F4）

        对每台受影响车辆独立执行 SHORTEST_TOTAL_TIME 贪心选择。
        """
        session = get_session()
        try:
            results = []
            for vehicle in vehicles:
                car_id = vehicle.get("car_id", "")
                amount = self._get_vehicle_request_amount(
                    car_id, vehicle, session,
                )
                charge_mode = self._get_vehicle_charge_mode(
                    car_id, vehicle, session,
                )
                if not charge_mode:
                    charge_mode = "FAST_CHARGE"

                pile_id, minutes = self._find_best_pile(
                    car_id, amount, charge_mode, session,
                )

                if pile_id:
                    self._update_request_pile(car_id, pile_id, session)
                    results.append({
                        "car_id": car_id,
                        "assigned_pile": pile_id,
                        "estimated_minutes": round(minutes, 1),
                        "success": True,
                    })
                else:
                    results.append({
                        "car_id": car_id,
                        "assigned_pile": "",
                        "estimated_minutes": 0,
                        "success": False,
                    })

            return results

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[SSD-F4] 失败: {str(e)}")
            return []
        finally:
            session.close()

    def batch_assign_by_shortest_total_time(self, vehicles: list,
                                            piles: list) -> list:
        """批量调度最短时长 — 匈牙利算法（SSD-F5）

        构建 N×M 成本矩阵 C[i][j] = w_j + (V_i.amount / P_j.max_power * 60)
        匈牙利算法求全局最优分配，O(N^3)。
        """
        session = get_session()
        try:
            n = len(vehicles)
            m = len(piles)
            if n == 0 or m == 0:
                return []

            INF = 1e10
            cost_matrix = []

            for vi in vehicles:
                row = []
                vi_amount = float(vi.get("request_amount", 50.0))
                vi_mode = vi.get("charging_mode", "")

                for pj in piles:
                    pj_power = float(pj.get("max_power_kw", 1))
                    pj_type = pj.get("type", "fast_charge")

                    # 兼容性检查
                    compatible = True
                    if vi_mode:
                        expected_type = (
                            "fast_charge" if vi_mode == "FAST_CHARGE"
                            else "slow_charge"
                        )
                        if pj_type != expected_type:
                            compatible = False

                    if compatible:
                        pj_id = pj.get("pile_id", "")
                        w = self._get_wait_minutes_for_pile(
                            pj_id, pj_power, session,
                        )
                        c = (vi_amount / pj_power) * 60.0
                        row.append(w + c)
                    else:
                        row.append(INF)

                cost_matrix.append(row)

            assignment = self._hungarian_algorithm(cost_matrix)

            results = []
            for i, j in enumerate(assignment):
                if j != -1 and j < m and cost_matrix[i][j] < INF / 2:
                    results.append({
                        "car_id": vehicles[i].get("car_id", f"V{i}"),
                        "assigned_pile": piles[j].get("pile_id", f"P{j}"),
                        "cost": round(cost_matrix[i][j], 2),
                    })
                else:
                    results.append({
                        "car_id": vehicles[i].get("car_id", f"V{i}"),
                        "assigned_pile": "",
                        "cost": float('inf'),
                    })

            return results

        except Exception as e:
            logger.error(LogModule.DISPATCH, f"[SSD-F5] 失败: {str(e)}")
            return []
        finally:
            session.close()

    # ==================================================================
    # 匈牙利算法实现
    # ==================================================================

    @staticmethod
    def _hungarian_algorithm(cost_matrix: list[list[float]]) -> list[int]:
        """标准匈牙利算法（Kuhn-Munkres），O(N^3)

        Args:
            cost_matrix: N×M 成本矩阵（N=车辆数，M=桩数）

        Returns:
            list[int]: result[i] = j 表示车辆 i 分配到桩 j，-1 表示未分配
        """
        n = len(cost_matrix)
        if n == 0:
            return []
        m = len(cost_matrix[0])
        if m == 0:
            return [-1] * n

        # 补成方阵
        size = max(n, m)
        matrix = [
            [cost_matrix[i][j] if i < n and j < m else 0.0
             for j in range(size)]
            for i in range(size)
        ]

        u = [0.0] * (size + 1)
        v = [0.0] * (size + 1)
        p = [0] * (size + 1)
        way = [0] * (size + 1)

        for i in range(1, size + 1):
            p[0] = i
            j0 = 0
            minv = [float('inf')] * (size + 1)
            used = [False] * (size + 1)
            while True:
                used[j0] = True
                i0 = p[j0]
                delta = float('inf')
                j1 = 0
                for j in range(1, size + 1):
                    if not used[j]:
                        cur = matrix[i0 - 1][j - 1] - u[i0] - v[j]
                        if cur < minv[j]:
                            minv[j] = cur
                            way[j] = j0
                        if minv[j] < delta:
                            delta = minv[j]
                            j1 = j
                for j in range(size + 1):
                    if used[j]:
                        u[p[j]] += delta
                        v[j] -= delta
                    else:
                        minv[j] -= delta
                j0 = j1
                if p[j0] == 0:
                    break
            while True:
                j1 = way[j0]
                p[j0] = p[j1]
                j0 = j1
                if j0 == 0:
                    break

        assignment = [-1] * n
        for j in range(1, size + 1):
            if p[j] - 1 < n and j - 1 < m:
                assignment[p[j] - 1] = j - 1
        return assignment
