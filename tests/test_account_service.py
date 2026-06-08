"""
账号服务单元测试

框架测试（PASS）：接口存在、参数校验、错误处理
业务测试（xfail）：依赖真实数据库和业务逻辑，mock 数据无法满足
"""

import pytest


class TestAccountServiceFramework:
    """框架层面：接口可调用、参数校验正常"""

    def test_create_account_called(self, account_service):
        """创建账号方法可调用且返回 dict"""
        result = account_service.create_account("京A12345", "张三", 60.0)
        assert isinstance(result, dict)
        assert "success" in result

    def test_create_account_invalid_capacity(self, account_service):
        """创建账号：电池容量无效触发热路径校验"""
        result = account_service.create_account("京A12345", "张三", 0)
        assert result["success"] is False
        assert "电池容量无效" in result["message"]

    def test_create_account_negative_capacity(self, account_service):
        """创建账号：负电池容量"""
        result = account_service.create_account("京A12345", "张三", -10.0)
        assert result["success"] is False

    def test_set_password_too_short(self, account_service):
        """设置密码：密码太短"""
        result = account_service.set_password("U20260001", "12345")
        assert result["success"] is False
        assert "密码长度" in result["message"]

    def test_authenticate_empty_credentials(self, account_service):
        """登录：空凭据校验"""
        result = account_service.authenticate("", "")
        assert result["success"] is False


class TestAccountServiceBusiness:
    """业务层面：数据库操作验证"""

    def test_create_account_generates_unique_id(self, account_service):
        """每次注册应生成不同的 user_id"""
        r1 = account_service.create_account("京A11111", "用户A", 60.0)
        r2 = account_service.create_account("京A22222", "用户B", 60.0)
        assert r1["user_id"] != r2["user_id"]

    def test_create_account_links_vehicle(self, account_service):
        """注册应同时创建车辆记录"""
        from src.db.database import get_session
        from src.db.models import Vehicle

        account_service.create_account("京A12345", "张三", 60.0)

        session = get_session()
        try:
            vehicle = session.query(Vehicle).filter(
                Vehicle.license_plate == "京A12345"
            ).first()
            assert vehicle is not None, "应创建车辆记录"
            assert float(vehicle.battery_capacity_kwh) == 60.0
        finally:
            session.close()

    def test_set_password_encrypts(self, account_service):
        """密码应加密存储，不存明文"""
        from src.db.database import get_session
        from src.db.models import User

        # 先注册
        reg = account_service.create_account("京A12345", "张三", 60.0)
        user_id = reg["user_id"]

        # 设置密码
        account_service.set_password(user_id, "Abc12345")

        # 验证 password_hash 是 bcrypt 密文
        session = get_session()
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            assert user is not None
            assert user.password_hash.startswith("$2b$"), "应为 bcrypt 密文"
            assert user.account_status == "ACTIVE"
        finally:
            session.close()

    def test_authenticate_verifies_password(self, account_service):
        """正确密码应登录成功，错误密码应失败"""
        reg = account_service.create_account("京A12345", "张三", 60.0)
        account_service.set_password(reg["user_id"], "Abc12345")

        login_ok = account_service.authenticate("京A12345", "Abc12345")
        assert login_ok["success"] is True

        login_fail = account_service.authenticate("京A12345", "wrong_password")
        assert login_fail["success"] is False

    def test_locked_account_cannot_login(self, account_service):
        """已锁定账号应拒绝登录"""
        from src.db.database import get_session
        from src.db.models import User

        reg = account_service.create_account("京A12345", "张三", 60.0)
        account_service.set_password(reg["user_id"], "Abc12345")

        # 将账号标记为 LOCKED
        session = get_session()
        try:
            user = session.query(User).filter(User.user_id == reg["user_id"]).first()
            user.account_status = "LOCKED"
            session.commit()
        finally:
            session.close()

        # 锁定后应登录失败
        result = account_service.authenticate("京A12345", "Abc12345")
        assert result["success"] is False
        assert "已锁定" in result["message"]
