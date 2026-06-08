"""
调度策略管理 — DispatchStrategy

职责：
- 系统启动时从配置文件加载默认策略
- 管理员运行时切换分配算法和故障策略
- 切换记录持久化到 dispatch_strategy_logs 表 + 同步写回配置
- 后续所有调度操作按当前激活策略执行
"""

from datetime import datetime

import yaml

from src.config import config
from src.db.database import get_session
from src.db.models import DispatchStrategyLog
from src.enums import LogLevel, LogModule
from src.utils.logger import logger


class DispatchStrategy:
    """调度策略管理器"""

    # 可用策略列表（不可变）
    AVAILABLE_ALGORITHMS = ["SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME"]
    AVAILABLE_FAULT_STRATEGIES = [
        "PRIORITY", "TIME_ORDER", "FAULT_RECOVERY",
        "SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME",
    ]

    def __init__(self):
        self._algorithm: str = "SHORTEST_TOTAL_TIME"
        self._fault_strategy: str = "TIME_ORDER"

    # ------------------------------------------------------------------
    # init: 从配置文件加载默认策略
    # ------------------------------------------------------------------
    def init(self) -> None:
        """从配置文件初始化调度策略

        读取 config/application.yml → dispatch 段，设置默认策略。
        在系统启动时由 main.py 调用。
        """
        self._algorithm = config.dispatch.default_algorithm
        self._fault_strategy = config.dispatch.default_fault_strategy

        logger.info(
            LogModule.SYSTEM,
            f"[策略] 初始化: algorithm={self._algorithm}, fault={self._fault_strategy}",
        )

        # 记录首次初始化日志
        self._log_change("SYSTEM", "ALGORITHM", "", self._algorithm)
        self._log_change("SYSTEM", "FAULT_STRATEGY", "", self._fault_strategy)

    # ------------------------------------------------------------------
    # switchAlgorithm: 运行时切换分配策略
    # ------------------------------------------------------------------
    def switch_algorithm(self, algorithm: str) -> dict:
        """切换分配策略

        验证 → 更新内存 → 写 dispatch_strategy_logs 表 → 同步配置文件 → 日志

        Args:
            algorithm: SHORTEST_TOTAL_TIME | BATCH_SHORTEST_TIME

        Returns:
            {"success": True, "current_algorithm": "BATCH_SHORTEST_TIME"}
            {"success": False, "message": "未知策略: xxx"}
        """
        if algorithm not in self.AVAILABLE_ALGORITHMS:
            return {"success": False, "message": f"未知策略: {algorithm}"}

        old_value = self._algorithm
        self._algorithm = algorithm

        # 持久化
        self._log_change("ADMIN", "ALGORITHM", old_value, algorithm)
        self._sync_to_config(self._algorithm, self._fault_strategy)

        logger.notice(
            LogModule.DISPATCH,
            f"[策略] 切换分配策略: {old_value} -> {algorithm}",
        )
        return {"success": True, "current_algorithm": algorithm}

    # ------------------------------------------------------------------
    # switchFault: 运行时切换故障策略
    # ------------------------------------------------------------------
    def switch_fault(self, fault_type: str) -> dict:
        """切换故障处理策略"""
        if fault_type not in self.AVAILABLE_FAULT_STRATEGIES:
            return {"success": False, "message": f"未知故障策略: {fault_type}"}

        old_value = self._fault_strategy
        self._fault_strategy = fault_type

        self._log_change("ADMIN", "FAULT_STRATEGY", old_value, fault_type)
        self._sync_to_config(self._algorithm, self._fault_strategy)

        logger.notice(
            LogModule.DISPATCH,
            f"[策略] 切换故障策略: {old_value} -> {fault_type}",
        )
        return {"success": True, "current_fault_strategy": fault_type}

    # ------------------------------------------------------------------
    # getCurrentAlgorithm / getCurrentFaultStrategy
    # ------------------------------------------------------------------
    def get_current_algorithm(self) -> str:
        return self._algorithm

    def get_current_fault_strategy(self) -> str:
        return self._fault_strategy

    def get_status(self) -> dict:
        return {
            "current_algorithm": self._algorithm,
            "current_fault_strategy": self._fault_strategy,
            "available_algorithms": self.AVAILABLE_ALGORITHMS,
            "available_fault_strategies": self.AVAILABLE_FAULT_STRATEGIES,
        }

    # ------------------------------------------------------------------
    # 内部方法
    # ------------------------------------------------------------------

    @staticmethod
    def _log_change(operator: str, change_type: str, from_value: str, to_value: str):
        """写入 dispatch_strategy_logs 表"""
        session = get_session()
        try:
            now = datetime.now()
            log = DispatchStrategyLog(
                operator=operator,
                change_type=change_type,
                from_value=from_value,
                to_value=to_value,
                change_time=now,
                created_at=now,
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(LogModule.DISPATCH,
                         f"[策略] 日志写入失败: {e}")
        finally:
            session.close()

    @staticmethod
    def _sync_to_config(algorithm: str, fault_strategy: str):
        """将当前策略同步回 config/application.yml 并 reload

        Args:
            algorithm: 当前分配策略标识符
            fault_strategy: 当前故障策略标识符
        """
        try:
            cfg_path = config._config_path

            # 测试环境下不写入共享的配置文件，避免测试间污染
            if cfg_path.name == "test_config.yml":
                return

            with open(cfg_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)

            if raw is None:
                raw = {}

            raw.setdefault("dispatch", {})
            raw["dispatch"]["default_algorithm"] = algorithm
            raw["dispatch"]["default_fault_strategy"] = fault_strategy

            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.dump(raw, f, allow_unicode=True, default_flow_style=False)

            # 重新加载配置使新值生效
            config.reload()

        except Exception as e:
            logger.error(
                LogModule.SYSTEM,
                f"[配置] 策略写回配置文件失败: {e}",
            )
