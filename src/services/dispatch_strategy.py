"""
调度策略管理 — DispatchStrategy

职责：
- 系统启动时从配置文件加载默认策略
- 管理员运行时切换分配算法和故障策略
- 后续所有调度操作按当前激活策略执行
"""

from typing import Optional

# from src.config import config


class DispatchStrategy:
    """调度策略管理器"""

    # 可用策略
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

        在系统启动时调用，从 config/application.yml 读取 dispatch 段
        设置默认分配算法和默认故障策略。

        TODOs:
            1. algorithm = config.dispatch.default_algorithm
            2. fault_strategy = config.dispatch.default_fault_strategy
            3. logger.info("SYSTEM", f"[策略] 初始分配策略: {algorithm}, 故障策略: {fault_strategy}")
        """
        # TODO: 真实实现
        # from src.config import config
        # self._algorithm = config.dispatch.default_algorithm
        # self._fault_strategy = config.dispatch.default_fault_strategy
        self._algorithm = "SHORTEST_TOTAL_TIME"
        self._fault_strategy = "TIME_ORDER"

    # ------------------------------------------------------------------
    # switchAlgorithm: 运行时切换分配策略
    # ------------------------------------------------------------------
    def switch_algorithm(self, algorithm: str) -> dict:
        """切换分配策略

        Args:
            algorithm: 策略标识符（SHORTEST_TOTAL_TIME / BATCH_SHORTEST_TIME）

        Returns:
            {"success": True, "current_algorithm": "BATCH_SHORTEST_TIME"}
            {"success": False, "message": "未知策略"}
        """
        # TODO: 真实实现
        # 1. 校验 algorithm 是否在 AVAILABLE_ALGORITHMS 中
        # 2. if 不在 → return {"success": False, "message": "未知策略"}
        # 3. self._algorithm = algorithm
        # 4. 同步写回 config/application.yml
        # 5. logger.notice("ADMIN", f"[策略] 切换分配策略至 {algorithm}")
        # 6. return {"success": True, "current_algorithm": algorithm}
        if algorithm not in self.AVAILABLE_ALGORITHMS:
            return {"success": False, "message": f"未知策略: {algorithm}"}

        self._algorithm = algorithm
        return {"success": True, "current_algorithm": algorithm}

    # ------------------------------------------------------------------
    # switchFault: 运行时切换故障策略
    # ------------------------------------------------------------------
    def switch_fault(self, fault_type: str) -> dict:
        """切换故障处理策略

        Args:
            fault_type: 策略标识符

        Returns:
            {"success": True, "current_fault_strategy": "PRIORITY"}
            {"success": False, "message": "未知策略"}
        """
        if fault_type not in self.AVAILABLE_FAULT_STRATEGIES:
            return {"success": False, "message": f"未知故障策略: {fault_type}"}

        self._fault_strategy = fault_type
        return {"success": True, "current_fault_strategy": fault_type}

    # ------------------------------------------------------------------
    # getCurrentAlgorithm / getCurrentFaultStrategy
    # ------------------------------------------------------------------
    def get_current_algorithm(self) -> str:
        """获取当前分配策略标识符"""
        return self._algorithm

    def get_current_fault_strategy(self) -> str:
        """获取当前故障策略标识符"""
        return self._fault_strategy

    def get_status(self) -> dict:
        """获取策略状态（含可用策略列表）

        Returns:
            {"current_algorithm": "SHORTEST_TOTAL_TIME",
             "current_fault_strategy": "TIME_ORDER",
             "available_algorithms": [...],
             "available_fault_strategies": [...]}
        """
        return {
            "current_algorithm": self._algorithm,
            "current_fault_strategy": self._fault_strategy,
            "available_algorithms": self.AVAILABLE_ALGORITHMS,
            "available_fault_strategies": self.AVAILABLE_FAULT_STRATEGIES,
        }
