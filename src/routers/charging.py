"""
充电流程路由 — /api/charging

接口定义参考：docs/系统架构设计文档.md §5.1
覆盖用例：UC-02（充电申请）、UC-05（修改请求）、UC-08（开始充电）、UC-10（查看充电状态）、UC-11（结束充电）
"""

from typing import Optional

from fastapi import APIRouter, Query

from src.schemas.charging import (ChargingRequestRequest,
                                   ModifyAmountRequest, ModifyModeRequest,
                                   StartChargingRequest)
from src.services.dispatch_service import DispatchService
from src.services.queue_service import QueueService

router = APIRouter(prefix="/api/charging", tags=["充电流程"])

_dispatch = DispatchService()
_queue = QueueService()


@router.post("/requests", summary="提交充电申请", response_model=dict)
def create_charging_request(body: ChargingRequestRequest):
    """E_chargingRequest(car_Id, Request_Amount, Request_Mode)

    用户提交充电申请，系统分配最佳充电桩并进入排队区。

    **请求体示例：**
    ```json
    {
        "car_Id": "京A12345",
        "Request_Amount": 50.0,
        "Request_Mode": "FAST_CHARGE"
    }
    ```

    **成功响应：**
    ```json
    {
        "success": true,
        "car_position": 3,
        "car_state": "QUEUED",
        "queue_Num": "P001",
        "request_time": "2026-06-07T10:30:00"
    }
    ```

    **失败响应（无兼容桩）：**
    ```json
    {"success": false, "message": "无兼容充电桩可用"}
    ```
    """
    # TODO: 真实实现
    # 1. _dispatch.assign_charging_pile() → 获取最佳桩
    # 2. _queue.enqueue() → 入队
    # 3. 返回排队信息
    result = _dispatch.assign_charging_pile(
        body.car_id, body.request_amount, body.request_mode,
    )
    return {
        "success": result["success"],
        "car_position": result.get("queue_position", 1),
        "car_state": "QUEUED",
        "queue_Num": result.get("pile_id", ""),
        "request_time": "2026-06-07T10:30:00",
    }


@router.put("/requests/{car_id}/amount", summary="修改充电电量", response_model=dict)
def modify_amount(car_id: str, body: ModifyAmountRequest):
    """Modify_Amount(car_Id, Amount)

    用户在排队区或等待区修改目标充电电量。

    **请求体示例：**
    ```json
    {"car_Id": "京A12345", "Amount": 60.0}
    ```

    **响应：**
    ```json
    {"success": true, "message": "充电量已更新"}
    ```
    """
    # TODO: 更新 charging_requests.target_power_kwh
    return {"success": True, "message": "充电量已更新"}


@router.put("/requests/{car_id}/mode", summary="修改充电模式", response_model=dict)
def modify_mode(car_id: str, body: ModifyModeRequest):
    """Modify_Mode(car_Id, Mode)

    用户在排队区更换充电模式（快充/慢充），
    系统从原队列移除并加入新模式对应队列队尾。

    **请求体示例：**
    ```json
    {"car_Id": "京A12345", "Mode": "SLOW_CHARGE"}
    ```

    **响应：**
    ```json
    {"success": true, "message": "充电模式已更新"}
    ```
    """
    # TODO: 更新 charging_requests.charging_mode，重新排队
    return {"success": True, "message": "充电模式已更新"}


@router.get("/requests/{car_id}/state", summary="查询排队状态", response_model=dict)
def query_car_state(car_id: str):
    """Query_Car_State(car_id)

    查询车辆当前在队列中的排队位置、状态、所在充电桩。

    **成功响应：**
    ```json
    {
        "success": true,
        "car_Number_before_position": 3,
        "car_state": "QUEUED",
        "queue_Num": "P001",
        "request_time": "2026-06-07T10:30:00"
    }
    ```
    """
    result = _queue.get_car_state(car_id)
    return {
        "success": result["success"],
        "car_Number_before_position": result.get("cars_before", 0),
        "car_state": result.get("car_state", ""),
        "queue_Num": result.get("queue_num", ""),
        "request_time": result.get("request_time", ""),
    }


@router.post("/sessions", summary="开始充电", response_model=dict)
def start_charging(body: StartChargingRequest):
    """Start_Charging(car_id, ChargePileNum)

    用户进入充电区后核对协议和电量，确认开始充电。

    **请求体示例：**
    ```json
    {
        "car_id": "京A12345",
        "ChargePileNum": "P001"
    }
    ```

    **成功响应：**
    ```json
    {"success": true, "session_id": "S20260607001", "message": "开始充电"}
    ```
    """
    # TODO: 真实实现
    # 1. 校验充电桩状态
    # 2. 创建充电会话 INSERT INTO charging_sessions
    # 3. 更新充电桩状态 charging_piles.status='CHARGING', current_charging_count+=1
    # 4. 更新充电请求 zone_type='CHARGING_AREA', request_status='CHARGING'
    # 5. 返回会话ID
    return {
        "success": True,
        "session_id": "S20260607001",
        "message": "开始充电",
    }


@router.get("/sessions/{car_id}", summary="查询充电状态", response_model=dict)
def query_charging_state(car_id: str):
    """Query_Charging_State(car_id)

    查询充电中的实时进度信息。

    **成功响应：**
    ```json
    {
        "success": true,
        "car_id": "京A12345",
        "pile_id": "P001",
        "session_id": "S20260607001",
        "current_battery_percentage": 65.0,
        "charged_power_kwh": 30.0,
        "current_power_kw": 110.0,
        "estimated_remaining_minutes": 15.0,
        "current_period_price": 1.2,
        "accumulated_fee": 35.0,
        "start_time": "2026-06-07T10:30:00"
    }
    ```
    """
    # TODO: 查询 charging_sessions 表获取实时数据
    return {
        "success": True,
        "car_id": car_id,
        "pile_id": "P001",
        "session_id": "S20260607001",
        "current_battery_percentage": 65.0,
        "charged_power_kwh": 30.0,
        "current_power_kw": 110.0,
        "estimated_remaining_minutes": 15.0,
        "current_period_price": 1.2,
        "accumulated_fee": 35.0,
        "start_time": "2026-06-07T10:30:00",
    }


@router.delete("/sessions/{car_id}", summary="结束充电", response_model=dict)
def end_charging(
    car_id: str,
    charging_pile_num: str = Query(None, alias="ChargingPileNum"),
):
    """End_Charging(car_id, ChargingPileNum)

    结束充电（自动完成或用户主动终止），生成账单。

    **查询参数：**
    - `ChargingPileNum` (可选): 充电桩编号

    **成功响应：**
    ```json
    {
        "success": true,
        "bill_id": "B20260607001",
        "total_fee": 58.1,
        "message": "充电结束"
    }
    ```

    **成功响应：**
    ```json
    {
        "success": true,
        "bill_id": "B20260607001",
        "total_fee": 58.1,
        "message": "充电结束"
    }
    ```
    """
    # TODO: 真实实现
    # 1. 结束充电会话 UPDATE charging_sessions SET end_time=NOW(), session_status='COMPLETED'
    # 2. 更新充电桩累计数据
    # 3. 调用 BillingService.calculate_bill()
    # 4. 释放充电桩
    return {
        "success": True,
        "bill_id": "B20260607001",
        "total_fee": 58.1,
        "message": "充电结束",
    }
