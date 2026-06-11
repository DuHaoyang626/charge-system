"""
充电桩模型 (stations, station_protocols)

Station 表示一个充电桩站点，包含三个区域：
    - 排队区 (queue)    : 用户提交充电请求后先进入排队
    - 等待区 (waiting)  : 等待分配充电位
    - 充电区 (charging) : 正在充电

StationProtocol 为充电桩与充电协议的多对多关联表。
"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class Station(SQLModel, table=True):
    __tablename__ = "stations"

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(max_length=50, description="充电桩名称/编号")
    status: str = Field(default="running", max_length=20, description="运行状态: idle / running / stopped")

    # 容量
    queue_capacity: int = Field(default=5, description="排队区最大容量")
    waiting_capacity: int = Field(default=3, description="等待区最大容量")
    charging_capacity: int = Field(default=2, description="充电区最大容量")

    # 当前占用
    queue_count: int = Field(default=0, description="排队区当前数量")
    waiting_count: int = Field(default=0, description="等待区当前数量")
    charging_count: int = Field(default=0, description="充电区当前数量")

    # 计费
    base_service_fee: float = Field(default=5.0, description="基础服务费 (元)")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"onupdate": datetime.utcnow},
    )


class StationProtocol(SQLModel, table=True):
    __tablename__ = "station_protocols"

    station_id: int = Field(foreign_key="stations.id", primary_key=True)
    protocol_id: int = Field(foreign_key="protocols.id", primary_key=True)
