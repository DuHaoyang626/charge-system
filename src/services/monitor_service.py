"""
监控服务 — MonitorService

职责：
- 定时采集所有充电桩的实时工作状态
- 提供单桩/批量统计查询
- 刷新累计数据（充电次数、时长、容量）
"""

from datetime import datetime
from typing import Optional

from src.db.database import get_session
from src.db.models import ChargingPile
from src.enums import LogModule
from src.utils.logger import logger


class MonitorService:
    """充电桩状态监控服务"""

    # 工作状态映射（status → working_state，便于未来自定义展示）
    _WORKING_STATE_MAP = {
        "RUNNING": "RUNNING",
        "AVAILABLE": "AVAILABLE",
        "CHARGING": "CHARGING",
        "CLOSED": "CLOSED",
        "FAULT": "FAULT",
        "QUEUEING": "QUEUEING",
    }

    @staticmethod
    def _pile_to_stats(pile: ChargingPile) -> dict:
        """将 ChargingPile ORM 对象转换为统计字典"""
        return {
            "pile_id": pile.pile_id,
            "working_state": MonitorService._WORKING_STATE_MAP.get(
                pile.status, pile.status
            ),
            "total_charge_num": pile.total_charge_num or 0,
            "total_charge_time": float(pile.total_charge_time) if pile.total_charge_time else 0.0,
            "total_capacity": float(pile.total_capacity) if pile.total_capacity else 0.0,
            "current_charging_count": pile.current_charging_count or 0,
            "status": pile.status,
        }

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
        session = get_session()
        try:
            pile = (
                session.query(ChargingPile)
                .filter(ChargingPile.pile_id == pile_id)
                .first()
            )
            if not pile:
                logger.warn(
                    LogModule.MONITOR,
                    f"[监控] 充电桩不存在: {pile_id}",
                )
                return {"success": False, "message": f"充电桩 {pile_id} 不存在"}

            logger.info(
                LogModule.MONITOR,
                f"[监控] 查询充电桩状态: {pile_id} (status: {pile.status})",
            )
            return self._pile_to_stats(pile)

        except Exception as e:
            logger.error(
                LogModule.MONITOR,
                f"[监控] 获取充电桩状态异常: {pile_id} - {str(e)}",
            )
            return {"success": False, "message": str(e)}
        finally:
            session.close()

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
        session = get_session()
        try:
            piles = session.query(ChargingPile).all()

            logger.info(
                LogModule.MONITOR,
                f"[监控] 批量采集充电桩状态: 共 {len(piles)} 个",
            )

            return [self._pile_to_stats(p) for p in piles]

        except Exception as e:
            logger.error(
                LogModule.MONITOR,
                f"[监控] 批量采集充电桩状态异常: {str(e)}",
            )
            return []
        finally:
            session.close()

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
        session = get_session()
        try:
            pile = (
                session.query(ChargingPile)
                .filter(ChargingPile.pile_id == pile_id)
                .first()
            )
            if not pile:
                logger.warn(
                    LogModule.MONITOR,
                    f"[监控] 更新状态失败: 充电桩不存在 {pile_id}",
                )
                return {"success": False, "message": f"充电桩 {pile_id} 不存在"}

            old_status = pile.status
            pile.status = new_status
            pile.updated_at = datetime.now()
            session.commit()

            logger.notice(
                LogModule.MONITOR,
                f"[监控] 充电桩状态更新: {pile_id} {old_status} → {new_status}",
            )
            return {"success": True, "pile_id": pile_id, "status": new_status}

        except Exception as e:
            session.rollback()
            logger.error(
                LogModule.MONITOR,
                f"[监控] 更新充电桩状态异常: {pile_id} - {str(e)}",
            )
            return {"success": False, "message": str(e)}
        finally:
            session.close()
