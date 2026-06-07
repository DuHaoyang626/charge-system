"""
账号服务 — AccountService

职责：用户注册、认证、密码管理
接口设计参考：docs/系统架构设计文档.md §三
"""

from typing import Optional

# ============================================================
# TODO: 后续引入真实依赖
# from src.db.database import get_session
# from src.db.models import User, Vehicle
# from src.utils.logger import logger
# from passlib.hash import bcrypt
# ============================================================


class AccountService:
    """用户账号服务"""

    # ------------------------------------------------------------------
    # createNewAccount(car_Id, userName, car_Capacity)
    # 用例：UC-22 注册账号
    # 前置：car_Id 格式正确、car_Capacity > 0
    # 后置：创建 User + Vehicle 对象，账号状态为 INACTIVE
    # ------------------------------------------------------------------
    def create_account(self, car_id: str, user_name: str, car_capacity: float) -> dict:
        """创建新账号

        Args:
            car_id: 车牌号（同时也是登录账号）
            user_name: 用户名
            car_capacity: 电池容量（kWh），必须 > 0

        Returns:
            成功: {"success": True, "user_id": "U20260001", "message": "账号创建成功"}
            失败: {"success": False, "message": "账号已存在"} 等

        Examples:
            >>> svc = AccountService()
            >>> svc.create_account("京A12345", "张三", 60.0)
            {"success": True, "user_id": "U20260001", "message": "账号创建成功"}
        """
        # ------------------------------------------------------------------
        # TODO: 真实实现
        # 1. 检查车牌号是否已注册 → SELECT * FROM users WHERE license_plate = ?
        # 2. 若已存在 → return {"success": False, "message": "账号已存在，请直接登录"}
        # 3. 创建 User(user_id=gen_id(), user_name, license_plate, password_hash="",
        #            account_status="INACTIVE")
        # 4. 创建 Vehicle(vehicle_id=gen_id(), user_id, license_plate, battery_capacity_kwh)
        # 5. logger.info("ACCOUNT", f"[注册] 新用户注册成功 (car_Id: {car_id})")
        # 6. return {"success": True, "user_id": user_id, "message": "账号创建成功"}
        # ------------------------------------------------------------------
        if car_capacity <= 0:
            return {"success": False, "message": "电池容量无效"}

        # TODO: 模拟接口，返回固定值
        return {"success": True, "user_id": "U20260001", "message": "账号创建成功"}

    # ------------------------------------------------------------------
    # set_pwd(password)
    # 用例：UC-22 注册账号（子步骤）
    # 前置：create_account 已成功执行，账号状态为 INACTIVE
    # 后置：密码加密存储，账号状态更新为 ACTIVE
    # ------------------------------------------------------------------
    def set_password(self, user_id: str, password: str) -> dict:
        """设置/修改密码

        Args:
            user_id: 用户编号
            password: 明文密码（长度 >= 6）

        Returns:
            {"success": True, "message": "密码设置成功"}
            {"success": False, "message": "密码强度不足"} 等

        Examples:
            >>> svc.set_password("U20260001", "Abc12345")
            {"success": True, "message": "密码设置成功"}
        """
        # TODO: 真实实现
        # 1. 验证密码强度（长度 >= 6，包含字母+数字）
        # 2. password_hash = bcrypt.hash(password)
        # 3. UPDATE users SET password_hash=?, account_status='ACTIVE', updated_at=NOW()
        # 4. logger.notice("ACCOUNT", f"[密码] 用户 {user_id} 密码已设置")
        # 5. return {"success": True, "message": "密码设置成功"}
        if len(password) < 6:
            return {"success": False, "message": "密码长度不能少于6位"}

        return {"success": True, "message": "密码设置成功"}

    # ------------------------------------------------------------------
    # login(car_Id, password)
    # 用例：UC-01 登录系统
    # 前置：用户已注册且账号状态为 ACTIVE
    # 后置：验证密码，记录登录时间，返回 access_token
    # ------------------------------------------------------------------
    def authenticate(self, car_id: str, password: str) -> dict:
        """用户登录认证

        Args:
            car_id: 车牌号
            password: 密码

        Returns:
            成功: {"success": True, "token": "xxx.yyy.zzz", "user_id": "U20260001", ...}
            失败: {"success": False, "message": "账号或密码错误"}

        Examples:
            >>> svc.authenticate("京A12345", "Abc12345")
            {"success": True, "token": "eyJ...", "user_id": "U20260001",
             "user_name": "张三", "membership_level": 1}
        """
        # TODO: 真实实现
        # 1. SELECT * FROM users WHERE license_plate = ?
        # 2. if not user → return {"success": False, "message": "账号不存在"}
        # 3. if user.account_status == "LOCKED" → return {"success": False, "message": "账号已锁定"}
        # 4. if !bcrypt.verify(password, user.password_hash) → return {"success": False, "message": "密码错误"}
        # 5. token = jwt.encode({"sub": user.user_id, "exp": ...}, SECRET_KEY)
        # 6. UPDATE users SET last_login_at=NOW()
        # 7. logger.info("ACCOUNT", f"[登录] 用户登录成功 (car_Id: {car_id})")
        # 8. return {"success": True, "token": token, "user_id": user.user_id, ...}
        if car_id == "" or password == "":
            return {"success": False, "message": "账号或密码错误"}

        return {
            "success": True,
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJVMjAyNjAwMDEiLCJleHAiOjk5OTk5OTk5OTl9.TODO",
            "user_id": "U20260001",
            "user_name": "张三",
            "license_plate": car_id,
            "membership_level": 1,
        }
