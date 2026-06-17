"""
阶段 0 验证：项目可启动、数据库可初始化、种子数据正确。
运行：pytest tests/test_stage0_infrastructure.py -v
"""


def test_project_imports():
    """所有核心模块可导入"""
    from core.config import settings
    from core.database import engine, init_db
    from core.security import create_access_token, verify_token, get_password_hash
    from core.exceptions import AppException, Err
    from core.deps import get_current_user, get_current_admin
    from model.user import User
    from model.station import Station
    from model.protocol import Protocol
    from model.session import ChargingSession
    from model.bill import Bill
    from model.config import GlobalConfig, ElectricityPrice, ServiceFeeTier
    from scheduler.dispatch_loop import DispatchLoop
    assert True


def test_seed_data():
    """种子数据正确写入"""
    from sqlmodel import Session, select
    from core.database import engine
    from model.protocol import Protocol
    from model.station import Station
    from model.user import User

    with Session(engine) as db:
        protocols = db.exec(select(Protocol)).all()
        assert len(protocols) >= 3, f"协议数量不足: {len(protocols)}"

        stations = db.exec(select(Station)).all()
        assert len(stations) >= 2, f"充电桩数量不足: {len(stations)}"

        admin = db.exec(select(User).where(User.license_plate == "ADMIN")).first()
        assert admin is not None, "管理员账号未创建"
        assert admin.role == "admin"


def test_jwt_roundtrip():
    """JWT 签发与验签正常"""
    from core.security import create_access_token, verify_token

    token = create_access_token(user_id=1, role="user")
    payload = verify_token(token)
    assert payload is not None
    assert payload["user_id"] == 1
    assert payload["role"] == "user"


def test_password_hash():
    """密码哈希与校验正常"""
    from core.security import get_password_hash, verify_password

    hashed = get_password_hash("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)
