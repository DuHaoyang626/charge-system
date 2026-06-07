"""
SQLAlchemy ORM 模型 — 13 张表

完整表结构见 docs/数据设计说明.md §三。
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    DECIMAL,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """用户账号表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(32), unique=True, nullable=False)
    user_name = Column(String(50), nullable=False)
    license_plate = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    membership_level = Column(Integer, nullable=False, default=0)
    account_status = Column(String(16), nullable=False, default="INACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    last_login_at = Column(DateTime, nullable=True)


class Vehicle(Base):
    """车辆信息表"""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vehicle_id = Column(String(32), unique=True, nullable=False)
    user_id = Column(String(32), nullable=False)
    license_plate = Column(String(20), unique=True, nullable=False)
    battery_capacity_kwh = Column(DECIMAL(8, 2), nullable=False)
    current_battery_percentage = Column(DECIMAL(5, 2), nullable=False, default=0)
    charging_protocol = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ChargingPile(Base):
    """充电桩表"""
    __tablename__ = "charging_piles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_id = Column(String(16), unique=True, nullable=False)
    pile_name = Column(String(50), nullable=False)
    type = Column(String(16), nullable=False)  # fast_charge | slow_charge
    max_power_kw = Column(DECIMAL(6, 2), nullable=False)
    status = Column(String(16), nullable=False, default="AVAILABLE")
    total_charge_num = Column(Integer, nullable=False, default=0)
    total_charge_time = Column(DECIMAL(10, 2), nullable=False, default=0)
    total_capacity = Column(DECIMAL(12, 2), nullable=False, default=0)
    parking_spots = Column(Integer, nullable=False, default=1)
    current_charging_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class PileProtocol(Base):
    """充电桩协议关联表"""
    __tablename__ = "pile_protocols"
    __table_args__ = (UniqueConstraint("pile_id", "protocol"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_id = Column(String(16), nullable=False)
    protocol = Column(String(20), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class PileTariffConfig(Base):
    """充电桩计费规则表"""
    __tablename__ = "pile_tariff_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pile_id = Column(String(16), unique=True, nullable=False)
    peak_price = Column(DECIMAL(6, 4), nullable=False, default=1.2)
    normal_price = Column(DECIMAL(6, 4), nullable=False, default=0.8)
    valley_price = Column(DECIMAL(6, 4), nullable=False, default=0.4)
    base_service_fee = Column(DECIMAL(6, 2), nullable=False, default=5.0)
    time_coefficient = Column(DECIMAL(6, 4), nullable=False, default=0.5)
    overtime_penalty = Column(DECIMAL(6, 4), nullable=False, default=0.8)
    timeout_base_fee = Column(DECIMAL(6, 2), nullable=False, default=5.0)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ChargingRequest(Base):
    """充电请求表（同时承担三区队列管理职能）"""
    __tablename__ = "charging_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(32), unique=True, nullable=False)
    car_id = Column(String(20), nullable=False)
    pile_id = Column(String(16), nullable=False)
    request_time = Column(DateTime, nullable=False, default=datetime.now)
    charging_mode = Column(String(16), nullable=False)
    target_power_kwh = Column(DECIMAL(8, 2), nullable=False)
    request_status = Column(String(16), nullable=False, default="QUEUED")
    zone_type = Column(String(16), nullable=False, default="QUEUE_AREA")
    queue_position = Column(Integer, nullable=True)
    original_pile_id = Column(String(16), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class ChargingSession(Base):
    """充电会话表"""
    __tablename__ = "charging_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(32), unique=True, nullable=False)
    request_id = Column(String(32), nullable=False)
    car_id = Column(String(20), nullable=False)
    pile_id = Column(String(16), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    target_power_kwh = Column(DECIMAL(8, 2), nullable=False)
    charged_power_kwh = Column(DECIMAL(8, 2), nullable=False, default=0)
    current_power_kw = Column(DECIMAL(6, 2), nullable=True)
    charging_protocol = Column(String(20), nullable=False)
    fault_interrupted = Column(Boolean, nullable=False, default=False)
    interrupted_power_kwh = Column(DECIMAL(8, 2), nullable=True)
    session_status = Column(String(16), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class BillingRecord(Base):
    """账单记录表"""
    __tablename__ = "billing_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(String(32), unique=True, nullable=False)
    session_id = Column(String(32), nullable=False)
    car_id = Column(String(20), nullable=False)
    date = Column(Date, nullable=False)
    pile_id = Column(String(16), nullable=False)
    charge_amount = Column(DECIMAL(8, 2), nullable=False)
    charge_duration = Column(DECIMAL(8, 2), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    total_charge_fee = Column(DECIMAL(10, 2), nullable=False)
    total_service_fee = Column(DECIMAL(10, 2), nullable=False)
    total_fee = Column(DECIMAL(10, 2), nullable=False)
    payment_status = Column(String(16), nullable=False, default="UNPAID")
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class DetailedBill(Base):
    """详单记录表"""
    __tablename__ = "detailed_bills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    bill_id = Column(String(32), nullable=False)
    period_name = Column(String(16), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    period_duration = Column(DECIMAL(8, 2), nullable=False)
    period_charge_kwh = Column(DECIMAL(8, 2), nullable=False)
    unit_price = Column(DECIMAL(6, 4), nullable=False)
    charge_fee = Column(DECIMAL(10, 2), nullable=False)
    service_fee = Column(DECIMAL(10, 2), nullable=False)
    subtotal_fee = Column(DECIMAL(10, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class PaymentOrder(Base):
    """支付订单表"""
    __tablename__ = "payment_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String(32), unique=True, nullable=False)
    bill_id = Column(String(32), nullable=False)
    car_id = Column(String(20), nullable=False)
    total_amount = Column(DECIMAL(10, 2), nullable=False)
    payment_status = Column(String(16), nullable=False, default="UNPAID")
    payment_method = Column(String(16), nullable=True)
    payment_time = Column(DateTime, nullable=True)
    refund_time = Column(DateTime, nullable=True)
    refund_amount = Column(DECIMAL(10, 2), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class FaultEvent(Base):
    """故障事件表"""
    __tablename__ = "fault_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(32), unique=True, nullable=False)
    pile_id = Column(String(16), nullable=False)
    occurrence_time = Column(DateTime, nullable=False)
    recovery_time = Column(DateTime, nullable=True)
    severity_level = Column(Integer, nullable=False, default=1)
    fault_type = Column(String(32), nullable=False)
    fault_strategy_used = Column(String(32), nullable=False)
    affected_vehicle_count = Column(Integer, nullable=False, default=0)
    rescheduled_count = Column(Integer, nullable=False, default=0)
    handling_status = Column(String(16), nullable=False, default="PENDING")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    log_id = Column(String(32), unique=True, nullable=False)
    module = Column(String(32), nullable=False)
    level = Column(Integer, nullable=False)
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)


class DispatchStrategyLog(Base):
    """策略变更日志表"""
    __tablename__ = "dispatch_strategy_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operator = Column(String(50), nullable=False)
    change_type = Column(String(16), nullable=False)
    from_value = Column(String(32), nullable=False)
    to_value = Column(String(32), nullable=False)
    change_time = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
