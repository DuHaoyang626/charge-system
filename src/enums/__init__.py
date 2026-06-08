"""
智能充电桩调度计费系统 — 枚举类型定义

所有枚举集中在此文件中，供 services、schemas、db/models 引用。
"""

from enum import Enum, IntEnum


class ChargeMode(str, Enum):
    """充电模式"""
    FAST_CHARGE = "FAST_CHARGE"
    SLOW_CHARGE = "SLOW_CHARGE"


class PileStatus(str, Enum):
    """充电桩运行状态"""
    AVAILABLE = "AVAILABLE"
    QUEUEING = "QUEUEING"
    CHARGING = "CHARGING"
    RUNNING = "RUNNING"
    CLOSED = "CLOSED"
    FAULT = "FAULT"


class RequestStatus(str, Enum):
    """充电请求状态（贯穿排队→等待→充电生命周期）"""
    QUEUED = "QUEUED"
    WAITING = "WAITING"
    CHARGING = "CHARGING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ZoneType(str, Enum):
    """三区区域类型"""
    QUEUE_AREA = "QUEUE_AREA"
    WAITING_AREA = "WAITING_AREA"
    CHARGING_AREA = "CHARGING_AREA"


class PaymentStatus(str, Enum):
    """支付状态"""
    UNPAID = "UNPAID"
    PAID = "PAID"
    REFUNDED = "REFUNDED"


class AccountStatus(str, Enum):
    """用户账号状态"""
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"


class SessionStatus(str, Enum):
    """充电会话状态"""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    INTERRUPTED = "INTERRUPTED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class FaultHandlingStatus(str, Enum):
    """故障处理状态"""
    PENDING = "PENDING"
    HANDLING = "HANDLING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class LogLevel(IntEnum):
    """日志等级

    所有等级的日志均写入数据库 system_logs 表，
    等级 >= config.logging.console_threshold 的额外输出到终端。
    """
    INFO = 0
    NOTICE = 1
    WARN = 2
    ERROR = 3
    CRITICAL = 4


class LogModule(str, Enum):
    """日志来源模块"""
    SYSTEM = "SYSTEM"
    ACCOUNT = "ACCOUNT"
    DISPATCH = "DISPATCH"
    QUEUE = "QUEUE"
    BILLING = "BILLING"
    MONITOR = "MONITOR"
    ADMIN = "ADMIN"
    FAULT = "FAULT"
    SCHEDULER = "SCHEDULER"
    API = "API"
