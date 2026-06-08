"""
pytest 全局配置与 fixtures

测试使用临时文件数据库。
每个测试函数拥有独立数据库（通过 _db fixture 保证单次初始化）。
"""

import warnings
warnings.filterwarnings("ignore", category=ResourceWarning)

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import config as global_config
from src.db.database import init as db_init
from src.db.database import init_db as create_tables


def _seed_test_data():
    """将 test_config.yml 中的充电桩配置同步到 charging_piles 表，
    并插入计费测试所需的充电会话和账单数据。"""
    from datetime import datetime

    from src.db.database import get_session
    from src.db.models import BillingRecord, ChargingPile, ChargingSession, DetailedBill, PileProtocol

    session = get_session()
    try:
        # ── 同步充电桩配置 ────────────────────────────
        for pile_cfg in global_config.piles:
            existing = session.query(ChargingPile).filter(
                ChargingPile.pile_id == pile_cfg.id
            ).first()
            if not existing:
                pile = ChargingPile(
                    pile_id=pile_cfg.id,
                    pile_name=pile_cfg.name,
                    type=pile_cfg.type,
                    max_power_kw=pile_cfg.max_power_kw,
                    parking_spots=pile_cfg.parking_spots,
                )
                session.add(pile)

            # 同步协议
            for proto in pile_cfg.protocols:
                existing_proto = session.query(PileProtocol).filter(
                    PileProtocol.pile_id == pile_cfg.id,
                    PileProtocol.protocol == proto,
                ).first()
                if not existing_proto:
                    session.add(PileProtocol(pile_id=pile_cfg.id, protocol=proto))

        # ── 计费测试种子数据 ──────────────────────────
        # ChargingSession (for calculate_bill tests)
        existing_cs = session.query(ChargingSession).filter(
            ChargingSession.session_id == "S20260607001"
        ).first()
        if not existing_cs:
            session.add(ChargingSession(
                session_id="S20260607001",
                request_id="R20260607001",
                car_id="京A12345",
                pile_id="P001",
                start_time=datetime(2026, 6, 7, 10, 0, 0),
                end_time=datetime(2026, 6, 7, 11, 0, 0),
                target_power_kwh=50.0,
                charged_power_kwh=50.0,
                current_power_kw=50.0,
                charging_protocol="GB_STANDARD",
                session_status="COMPLETED",
            ))

        # BillingRecord (for get_detailed_bill test — session_id differs
        # so calculate_bill won't short-circuit on it)
        existing_br = session.query(BillingRecord).filter(
            BillingRecord.bill_id == "B20260607001"
        ).first()
        if not existing_br:
            session.add(BillingRecord(
                bill_id="B20260607001",
                session_id="S20260607999",
                car_id="京A12345",
                date=datetime(2026, 6, 7).date(),
                pile_id="P001",
                charge_amount=50.0,
                charge_duration=60.0,
                start_time=datetime(2026, 6, 7, 10, 0, 0),
                end_time=datetime(2026, 6, 7, 11, 0, 0),
                total_charge_fee=75.0,
                total_service_fee=35.0,
                total_fee=110.0,
                payment_status="UNPAID",
            ))

        # DetailedBill (one peak period for the above BillingRecord)
        existing_dtl = session.query(DetailedBill).filter(
            DetailedBill.bill_id == "B20260607001",
            DetailedBill.period_name == "peak",
        ).first()
        if not existing_dtl:
            session.add(DetailedBill(
                bill_id="B20260607001",
                period_name="peak",
                period_start=datetime(2026, 6, 7, 10, 0, 0),
                period_end=datetime(2026, 6, 7, 11, 0, 0),
                period_duration=60.0,
                period_charge_kwh=50.0,
                unit_price=1.5,
                charge_fee=75.0,
                service_fee=35.0,
                subtotal_fee=110.0,
            ))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _create_test_db() -> str:
    """创建临时数据库并初始化"""
    cfg_path = Path(__file__).parent / "test_config.yml"
    global_config.load(cfg_path)

    tmp = tempfile.NamedTemporaryFile(suffix="_test.db", delete=False)
    tmp.close()
    global_config.system.db_path = tmp.name

    db_init(tmp.name)
    create_tables()
    _seed_test_data()
    return tmp.name


@pytest.fixture(scope="function")
def _db():
    """每个测试函数创建独立的临时数据库"""
    from src.db.database import close as close_db

    db_path = _create_test_db()
    yield
    close_db()
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except (PermissionError, OSError):
        pass


@pytest.fixture(scope="function")
def account_service(_db):
    from src.services import AccountService
    return AccountService()


@pytest.fixture(scope="function")
def queue_service(_db):
    from src.services import QueueService
    return QueueService()


@pytest.fixture(scope="function")
def dispatch_service(_db):
    from src.services import DispatchService
    return DispatchService()


@pytest.fixture(scope="function")
def dispatch_strategy(_db):
    from src.services import DispatchStrategy
    ds = DispatchStrategy()
    ds.init()
    return ds


@pytest.fixture(scope="function")
def billing_service(_db):
    from src.services import BillingService
    return BillingService()


@pytest.fixture(scope="function")
def monitor_service(_db):
    from src.services import MonitorService
    return MonitorService()


@pytest.fixture(scope="function")
def client():
    """FastAPI TestClient（使用临时文件数据库）"""
    from src.db.database import close as close_db

    db_path = _create_test_db()

    from src.main import app
    with TestClient(app) as c:
        yield c

    close_db()
    try:
        if os.path.exists(db_path):
            os.unlink(db_path)
    except (PermissionError, OSError):
        pass
