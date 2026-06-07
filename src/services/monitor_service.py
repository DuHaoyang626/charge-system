"""
监控服务 — MonitorService

职责：
- 定时采集所有充电桩的实时工作状态
- 提供单桩/批量统计查询
- 刷新累计数据（充电次数、时长、容量）
"""

from typing import Optional


class MonitorService:
    """充电桩状态监控服务"""

    # ------------------------------------------------------------------
    # getPileStats: 获取单个充电桩状态和统计数据
    # ------------------------------------------------------------------
    def get_pile_stats(self, pile_id: str) -> dict:
        """获取充电桩状态

        Args:
            pile_id: 充电桩编号

        Returns:
            {"pile_id": "P001", "working_state": "RUNNING",
             "total_charge_num": 125,        # 累计充电次数
             "total_charge_time": 4560.5,    # 累计充电时长（分钟）
             "total_capacity": 8520.0,       # 累计充电容量（kWh）
             "current_charging_count": 2,    # 当前充电车辆数
             "status": "CHARGING"}           # 当前运行状态

        Examples:
            >>> ms = MonitorService()
            >>> ms.get_pile_stats("P001")
            {"pile_id": "P001", "working_state": "RUNNING", ...}
        """
        # TODO: 真实实现
        # SELECT * FROM charging_piles WHERE pile_id=?
        return {
            "pile_id": pile_id,
            "working_state": "RUNNING",
            "total_charge_num": 125,
            "total_charge_time": 4560.5,
            "total_capacity": 8520.0,
            "current_charging_count": 2,
            "status": "CHARGING",
        }

    # ------------------------------------------------------------------
    # batchCollectStats: 批量采集所有充电桩状态
    # ------------------------------------------------------------------
    def batch_collect_stats(self) -> list:
        """批量采集所有充电桩状态

        由 ScheduledTaskService 定时触发，刷新所有充电桩的实时状态。

        Returns:
            [{"pile_id": "P001", ...}, {"pile_id": "P002", ...}, ...]

        Examples:
            >>> ms.batch_collect_stats()
            [{"pile_id": "P001", ...}, {"pile_id": "P002", ...}]
        """
        # TODO: 真实实现
        # SELECT * FROM charging_piles WHERE 1=1
        return [
            {
                "pile_id": "P001",
                "working_state": "RUNNING",
                "total_charge_num": 125,
                "total_charge_time": 4560.5,
                "total_capacity": 8520.0,
                "current_charging_count": 2,
            },
            {
                "pile_id": "P002",
                "working_state": "RUNNING",
                "total_charge_num": 98,
                "total_charge_time": 3200.0,
                "total_capacity": 6800.0,
                "current_charging_count": 1,
            },
        ]

    # ------------------------------------------------------------------
    # refresh_pile_status: 刷新单桩运行状态（内部使用）
    # ------------------------------------------------------------------
    def refresh_pile_status(self, pile_id: str, new_status: str) -> dict:
        """更新充电桩运行状态

        Args:
            pile_id: 充电桩编号
            new_status: 新状态

        Returns:
            {"success": True, "pile_id": pile_id, "status": new_status}
        """
        # TODO: 真实实现
        # UPDATE charging_piles SET status=?, updated_at=NOW() WHERE pile_id=?
        return {"success": True, "pile_id": pile_id, "status": new_status}
