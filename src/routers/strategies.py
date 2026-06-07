"""
调度策略管理路由 — /api/strategies

接口定义参考：docs/系统架构设计文档.md §5.2
覆盖用例：UC-41（管理调度策略）、UC-42（设置启动默认）、UC-43（运行时切换）
"""

from fastapi import APIRouter

from src.schemas.admin import (CurrentStrategiesResponse,
                                SwitchStrategyRequest)
from src.schemas.user import SimpleResponse
from src.services.dispatch_strategy import DispatchStrategy

router = APIRouter(prefix="/api/strategies", tags=["调度策略"])

_strategy = DispatchStrategy()


@router.get("", summary="获取当前策略", response_model=dict)
def get_current_strategies():
    """getCurrentStrategies()

    获取当前激活的分配策略和故障策略，以及可选策略列表。

    **成功响应：**
    ```json
    {
        "success": true,
        "current_algorithm": "SHORTEST_TOTAL_TIME",
        "current_fault_strategy": "TIME_ORDER",
        "available_algorithms": ["SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME"],
        "available_fault_strategies": ["PRIORITY", "TIME_ORDER", "FAULT_RECOVERY",
                                        "SHORTEST_TOTAL_TIME", "BATCH_SHORTEST_TIME"]
    }
    ```
    """
    status = _strategy.get_status()
    return {"success": True, **status}


@router.put("/dispatch", summary="切换分配策略", response_model=dict)
def switch_dispatch_strategy(body: SwitchStrategyRequest):
    """switchDispatchStrategy(strategyType)

    运行时切换正常分配策略，切换后后续所有调度操作使用新策略。
    不影响正在进行的充电会话。

    **请求体示例：**
    ```json
    {"strategy_type": "BATCH_SHORTEST_TIME"}
    ```

    **成功响应：**
    ```json
    {"success": true, "current_algorithm": "BATCH_SHORTEST_TIME"}
    ```

    **失败响应：**
    ```json
    {"success": false, "message": "未知策略: INVALID"}
    ```
    """
    return _strategy.switch_algorithm(body.strategy_type)


@router.put("/fault", summary="切换故障策略", response_model=dict)
def switch_fault_strategy(body: SwitchStrategyRequest):
    """switchFaultStrategy(faultType)

    运行时切换故障处理策略，切换后后续故障事件使用新策略处理。

    **请求体示例：**
    ```json
    {"strategy_type": "PRIORITY"}
    ```

    **成功响应：**
    ```json
    {"success": true, "current_fault_strategy": "PRIORITY"}
    ```
    """
    return _strategy.switch_fault(body.strategy_type)
