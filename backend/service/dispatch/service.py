"""
调度服务 — 最优充电桩计算。

DispatchService.findBestStation()
    筛选 running 且排队区未满的桩 → 筛选兼容用户协议的桩 → 按排队人数升序。
"""

import logging

from sqlmodel import Session, select

from core.database import engine
from model.protocol import Protocol
from model.station import Station, StationProtocol

logger = logging.getLogger("charge-system.dispatch")


def find_best_station(user_id: int, protocol_ids: list[int]) -> Station | None:
    """
    为充电请求选择最优充电桩。

    算法：
    1. 筛选 status = 'running' 的桩
    2. 筛选 queue_count < queue_capacity（排队区未满）
    3. 筛选支持用户所选协议的桩
    4. 按排队人数升序排列，选排队最短的

    返回 Station or None（无可用桩时）。
    """
    with Session(engine) as db:
        # 获取所有 running 的桩
        stations = db.exec(
            select(Station).where(
                Station.status == "running",
                Station.queue_count < Station.queue_capacity,
            )
        ).all()

        if not stations:
            return None

        # 获取协议 ID → 桩 ID 映射
        sp_rows = db.exec(
            select(StationProtocol).where(
                StationProtocol.protocol_id.in_(protocol_ids)
            )
        ).all()

        # 桩 ID → 支持的协议 ID 列表
        station_protocols_map: dict[int, set[int]] = {}
        for sp in sp_rows:
            if sp.station_id not in station_protocols_map:
                station_protocols_map[sp.station_id] = set()
            station_protocols_map[sp.station_id].add(sp.protocol_id)

        protocol_set = set(protocol_ids)

        # 筛选兼容的桩
        compatible = [
            s for s in stations
            if s.id in station_protocols_map
            and protocol_set & station_protocols_map[s.id]  # 至少一个协议匹配
        ]

        if not compatible:
            return None

        # 按排队人数升序排列
        compatible.sort(key=lambda s: s.queue_count)

        return compatible[0]
