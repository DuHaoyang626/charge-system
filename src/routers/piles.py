"""
充电桩管理路由 — /api/piles

接口定义参考：docs/系统架构设计文档.md §5.2
覆盖用例：UC-17（控制充电桩可用性）、UC-18（修改参数）、UC-23（运行充电桩）、UC-14（查看状态）
"""

from fastapi import APIRouter

from src.schemas.admin import PileStateResponse, SetParametersRequest
from src.schemas.user import SimpleResponse
from src.services.monitor_service import MonitorService

router = APIRouter(prefix="/api/piles", tags=["充电桩管理"])

_monitor = MonitorService()


@router.post("/{pile_id}/power/on", summary="启动充电桩电源", response_model=dict)
def power_on(pile_id: str):
    """powerOn(pile_Id)

    开启指定充电桩的电源，使其进入可用状态。

    **成功响应：**
    ```json
    {"success": true, "message": "充电桩电源已开启"}
    ```

    **失败响应：**
    ```json
    {"success": false, "message": "充电桩不存在"}
    ```
    """
    # TODO: 真实实现
    # 1. 校验充电桩存在
    # 2. UPDATE charging_piles SET status='AVAILABLE'
    # 3. logger.notice("ADMIN", f"[管理] powerOn (pile_id: {pile_id})")
    return {"success": True, "message": "充电桩电源已开启"}


@router.put("/{pile_id}/parameters", summary="设置充电桩参数", response_model=dict)
def set_parameters(pile_id: str, body: SetParametersRequest):
    """setParameters(pile_Id, 计费规则, 电价数据)

    设置充电桩的计费规则和三时段电价数据。
    设置的值会存入 pile_tariff_configs 表。

    **请求体示例：**
    ```json
    {
        "pile_Id": "P001",
        "peak_price": 1.5,
        "normal_price": 1.0,
        "valley_price": 0.5,
        "base_service_fee": 5.0,
        "time_coefficient": 0.5
    }
    ```

    **成功响应：**
    ```json
    {"success": true, "message": "参数设置成功"}
    ```
    """
    # TODO: 真实实现
    # 1. UPSERT INTO pile_tariff_configs
    # 2. 同步写回 config/application.yml
    # 3. logger.notice("ADMIN", f"[管理] 更新 {pile_id} 计费规则")
    return {"success": True, "message": "参数设置成功"}


@router.post("/{pile_id}/run", summary="运行充电桩", response_model=dict)
def start_charging_pile(pile_id: str):
    """Start_ChargingPile(pile_Id)

    将充电桩从"可用"状态切换为"运行中"状态，
    使其可接受充电请求。

    **成功响应：**
    ```json
    {"success": true, "message": "充电桩已进入运行状态"}
    ```
    """
    # TODO: UPDATE charging_piles SET status='RUNNING'
    return {"success": True, "message": "充电桩已进入运行状态"}


@router.post("/{pile_id}/power/off", summary="关闭充电桩", response_model=dict)
def power_off(pile_id: str):
    """powerOff(pile_Id)

    关闭充电桩电源。如充电桩正在充电中则拒绝操作。

    **成功响应：**
    ```json
    {"success": true, "message": "充电桩已关闭"}
    ```

    **失败响应（充电中）：**
    ```json
    {"success": false, "message": "充电桩正在使用中，无法关机"}
    ```
    """
    # TODO: 检查 current_charging_count > 0 → 拒绝
    return {"success": True, "message": "充电桩已关闭"}


@router.get("/{pile_id}/state", summary="查看充电桩状态", response_model=dict)
def query_pile_state(pile_id: str):
    """Query_PileState(pile_Id)

    查看充电桩的实时工作状态和累计统计数据。

    **成功响应：**
    ```json
    {
        "success": true,
        "pile_id": "P001",
        "working_state": "RUNNING",
        "total_charge_num": 125,
        "total_charge_time": 4560.5,
        "total_capacity": 8520.0
    }
    ```
    """
    stats = _monitor.get_pile_stats(pile_id)
    return {"success": True, **stats}
