"""
账号服务 — 注册、登录、获取用户信息的业务逻辑。
"""

import logging

from sqlmodel import Session, select

from core.database import engine
from core.exceptions import AppException, Err
from core.security import create_access_token, get_password_hash, verify_password
from model.protocol import Protocol
from model.station import Station
from model.user import User
from model.user_protocol import UserProtocol

logger = logging.getLogger("charge-system.account")


def register(
    license_plate: str,
    user_name: str,
    battery_capacity: float,
    password: str,
    protocol_ids: list[int],
    phone: str | None = None,
) -> dict:
    """
    用户注册。

    返回: {"userId": int, "licensePlate": str, "userName": str, "token": str}
    """
    with Session(engine) as db:
        # 1. 校验车牌号唯一
        existing = db.exec(
            select(User).where(User.license_plate == license_plate)
        ).first()
        if existing:
            raise AppException(*Err.LICENSE_PLATE_EXISTS)

        # 2. 校验协议 ID 是否存在
        existing_protocols = db.exec(
            select(Protocol).where(Protocol.id.in_(protocol_ids))
        ).all()
        existing_ids = {p.id for p in existing_protocols}
        for pid in protocol_ids:
            if pid not in existing_ids:
                raise AppException(400, f"协议 ID {pid} 不存在")

        # 3. 创建用户
        user = User(
            license_plate=license_plate,
            user_name=user_name,
            password=get_password_hash(password),
            battery_capacity=battery_capacity,
            role="user",
            phone=phone or None,
            balance=0,
        )
        db.add(user)
        db.flush()

        # 4. 关联用户协议
        for pid in protocol_ids:
            db.add(UserProtocol(user_id=user.id, protocol_id=pid))

        db.commit()
        db.refresh(user)

    token = create_access_token(user_id=user.id, role=user.role)
    return {
        "userId": user.id,
        "licensePlate": user.license_plate,
        "userName": user.user_name,
        "token": token,
    }


def login(license_plate: str, password: str) -> dict:
    """
    用户登录。

    返回: {"userId": int, "licensePlate": str, "userName": str, "token": str, "role": str}
    """
    with Session(engine) as db:
        user = db.exec(
            select(User).where(User.license_plate == license_plate)
        ).first()

        # 防撞库：账号不存在和密码错误返回相同信息
        if user is None or not verify_password(password, user.password):
            raise AppException(*Err.INVALID_CREDENTIALS)

    token = create_access_token(user_id=user.id, role=user.role)
    return {
        "userId": user.id,
        "licensePlate": user.license_plate,
        "userName": user.user_name,
        "token": token,
        "role": user.role,
    }


def get_user_info(user_id: int) -> dict:
    """
    获取当前用户完整信息。

    返回: 包含 userId, licensePlate, userName, phone, batteryCapacity,
          protocols, activeSession 的 dict。
    """
    with Session(engine) as db:
        user = db.get(User, user_id)
        if user is None:
            raise AppException(*Err.NOT_FOUND)

        # 查询用户支持的协议
        up_rows = db.exec(
            select(UserProtocol, Protocol)
            .join(Protocol, UserProtocol.protocol_id == Protocol.id)
            .where(UserProtocol.user_id == user_id)
        ).all()
        protocols = [
            {
                "id": p.id,
                "name": p.name,
                "powerKw": p.power_kw,
            }
            for _, p in up_rows
        ]

        # 查询进行中的会话
        from model.session import ChargingSession

        active_session = db.exec(
            select(ChargingSession)
            .where(
                ChargingSession.user_id == user_id,
                ChargingSession.status.in_(["queued", "waiting", "charging"]),
            )
            .order_by(ChargingSession.created_at.desc())
            .limit(1)
        ).first()

        active_session_data = None
        if active_session:
            station = db.get(Station, active_session.station_id)
            progress = 0
            if (
                active_session.status == "charging"
                and active_session.requested_energy_kwh > 0
            ):
                progress = min(
                    100,
                    int(
                        active_session.charged_energy_kwh
                        / active_session.requested_energy_kwh
                        * 100
                    ),
                )
            active_session_data = {
                "sessionId": active_session.id,
                "status": active_session.status,
                "stationName": station.name if station else "",
                "progress": progress,
            }

        return {
            "userId": user.id,
            "licensePlate": user.license_plate,
            "userName": user.user_name,
            "phone": user.phone,
            "batteryCapacity": user.battery_capacity,
            "protocols": protocols,
            "activeSession": active_session_data,
        }
