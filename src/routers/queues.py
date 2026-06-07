"""
队列管理路由 — /api/queues

接口定义参考：docs/系统架构设计文档.md §5.2
覆盖用例：UC-15（查看队列状态）
"""

from fastapi import APIRouter, Query

from src.services.queue_service import QueueService

router = APIRouter(prefix="/api/queues", tags=["队列管理"])

_svc = QueueService()


@router.get("/state", summary="查看队列状态", response_model=dict)
def query_queue_state(queuelist: str = Query(..., description="充电桩编号列表，逗号分隔")):
    """Query_QueueState(queuelist)

    管理员查看指定充电桩队列中的车辆详情。

    **查询参数：**
    - `queuelist` (必填): 充电桩编号列表，逗号分隔，如 "P001,P002"

    **成功响应：**
    ```json
    {
        "success": true,
        "queues": [
            {
                "pile_id": "P001",
                "zone_type": "QUEUE_AREA",
                "vehicles": [
                    {
                        "car_Id": "京A12345",
                        "car_Capacity": 60.0,
                        "Request_Amount": 50.0,
                        "waitTime": 15.0
                    }
                ]
            }
        ]
    }
    ```
    """
    pile_ids = [p.strip() for p in queuelist.split(",") if p.strip()]
    queues = _svc.get_queue_detail(pile_ids)
    return {"success": True, "queues": queues}
