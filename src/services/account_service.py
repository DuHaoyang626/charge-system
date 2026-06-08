"""
账号服务 — AccountService

职责：用户注册、认证、密码管理
"""

from datetime import datetime, timedelta

from jose import jwt
from passlib.hash import bcrypt
from sqlalchemy import update

from src.config import config
from src.db.database import get_session
from src.db.models import User, Vehicle
from src.enums import LogModule
from src.utils.logger import logger


class AccountService:
    """用户账号服务"""

    @staticmethod
    def _gen_user_id() -> str:
        """生成用户编号（格式: U + 时间戳+微秒）"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d%H%M%S%f")
        return f"U{date_str}"

    @staticmethod
    def _gen_vehicle_id() -> str:
        """生成车辆编号"""
        now = datetime.now()
        date_str = now.strftime("%Y%m%d%H%M%S%f")
        return f"V{date_str}"

    # ------------------------------------------------------------------
    # createNewAccount(car_Id, userName, car_Capacity)
    # ------------------------------------------------------------------
    def create_account(self, car_id: str, user_name: str, car_capacity: float) -> dict:
        """创建新账号"""
        if car_capacity <= 0:
            return {"success": False, "message": "电池容量无效"}

        session = get_session()
        try:
            # 检查是否已注册
            existing = session.query(User).filter(
                User.license_plate == car_id
            ).first()
            if existing:
                return {"success": False, "message": "账号已存在，请直接登录"}

            # 创建用户（初始状态 INACTIVE，待设置密码）
            user_id = self._gen_user_id()
            now = datetime.now()
            user = User(
                user_id=user_id,
                user_name=user_name,
                license_plate=car_id,
                password_hash="",
                membership_level=0,
                account_status="INACTIVE",
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.flush()

            # 创建车辆记录
            vehicle = Vehicle(
                vehicle_id=self._gen_vehicle_id(),
                user_id=user_id,
                license_plate=car_id,
                battery_capacity_kwh=car_capacity,
                current_battery_percentage=0,
                created_at=now,
                updated_at=now,
            )
            session.add(vehicle)
            session.commit()

            logger.info(LogModule.ACCOUNT,
                        f"[注册] 新用户注册成功 (car_Id: {car_id}, user_id: {user_id})")
            return {"success": True, "user_id": user_id, "message": "账号创建成功"}

        except Exception as e:
            session.rollback()
            logger.error(LogModule.ACCOUNT,
                         f"[注册] 注册失败 (car_Id: {car_id}, error: {str(e)})")
            return {"success": False, "message": f"注册失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # set_pwd(password)
    # ------------------------------------------------------------------
    def set_password(self, user_id: str, password: str) -> dict:
        """设置/修改密码"""
        if len(password) < 6:
            return {"success": False, "message": "密码长度不能少于6位"}

        session = get_session()
        try:
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {"success": False, "message": "用户不存在"}

            # bcrypt 加密存储
            password_hash = bcrypt.hash(password)
            now = datetime.now()
            user.password_hash = password_hash
            user.account_status = "ACTIVE"
            user.updated_at = now
            session.commit()

            logger.notice(LogModule.ACCOUNT,
                          f"[密码] 用户 {user_id} 密码已设置 (account_status: ACTIVE)")
            return {"success": True, "message": "密码设置成功"}

        except Exception as e:
            session.rollback()
            logger.error(LogModule.ACCOUNT,
                         f"[密码] 密码设置失败 (user_id: {user_id}, error: {str(e)})")
            return {"success": False, "message": f"密码设置失败: {str(e)}"}
        finally:
            session.close()

    # ------------------------------------------------------------------
    # login(car_Id, password)
    # ------------------------------------------------------------------
    def authenticate(self, car_id: str, password: str) -> dict:
        """用户登录认证"""
        if car_id == "" or password == "":
            return {"success": False, "message": "账号或密码错误"}

        session = get_session()
        try:
            user = session.query(User).filter(
                User.license_plate == car_id
            ).first()

            if not user:
                return {"success": False, "message": "账号不存在"}

            if user.account_status == "LOCKED":
                return {"success": False, "message": "账号已锁定，请联系管理员"}

            if not user.password_hash or not bcrypt.verify(password, user.password_hash):
                logger.notice(LogModule.ACCOUNT,
                              f"[登录] 登录失败: 密码错误 (car_Id: {car_id})")
                return {"success": False, "message": "账号或密码错误"}

            # 生成 JWT token
            now = datetime.now()
            payload = {
                "sub": user.user_id,
                "car_id": car_id,
                "exp": now + timedelta(minutes=config.system.token_expire_minutes),
                "iat": now,
            }
            token = jwt.encode(payload, config.system.jwt_secret, algorithm="HS256")

            # 更新最后登录时间
            user.last_login_at = now
            user.updated_at = now
            session.commit()

            logger.info(LogModule.ACCOUNT,
                        f"[登录] 用户登录成功 (car_Id: {car_id}, user_id: {user.user_id})")
            return {
                "success": True,
                "token": token,
                "user_id": user.user_id,
                "user_name": user.user_name,
                "license_plate": car_id,
                "membership_level": user.membership_level,
            }

        except Exception as e:
            session.rollback()
            logger.error(LogModule.ACCOUNT,
                         f"[登录] 登录异常 (car_Id: {car_id}, error: {str(e)})")
            return {"success": False, "message": f"登录异常: {str(e)}"}
        finally:
            session.close()
