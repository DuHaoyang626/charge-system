"""
自定义业务异常 + 预定义错误码。

使用方式：
    raise AppException(*Err.NOT_FOUND)
    raise AppException(*Err.SESSION_CONFLICT)
"""


class AppException(Exception):
    """业务异常，由全局异常处理器捕获并返回统一格式响应。"""

    def __init__(self, code: int = 400, message: str = "请求失败"):
        self.code = code
        self.message = message
        super().__init__(self.message)


class Err:
    """预定义错误码枚举。

    每个属性为 (http_status_code, message) 元组，可直接解包传给 AppException。
    """

    # ── 通用 ──
    NOT_FOUND = (404, "资源不存在")
    UNAUTHORIZED = (401, "未登录或 Token 已过期")
    FORBIDDEN = (403, "无权访问")

    # ── 充电会话 ──
    SESSION_CONFLICT = (409, "您已有进行中的充电会话")
    QUEUE_FULL = (400, "当前所有充电桩排队区已满")
    NOT_CHARGING = (400, "当前不在充电状态")
    ENERGY_TOO_LOW = (400, "新电量必须大于已充电量")
    ENERGY_INVALID = (400, "目标电量必须大于 0")
    SESSION_COMPLETED = (400, "会话已结束，不可修改")
    CANNOT_CANCEL_CHARGING = (400, "充电中不可取消，请使用停止充电接口")
    CANNOT_SWITCH_WAITING = (400, "等待区中不可换队")

    # ── 充电桩 ──
    STATION_NOT_FOUND = (404, "充电桩不存在")
    STATION_NOT_RUNNING = (400, "充电桩已停止运行")
    STATION_HAS_VEHICLES = (400, "充电桩仍有车辆，无法删除")
    STATION_CANNOT_DELETE = (400, "充电桩仍有车辆，无法删除")
    TARGET_STATION_FULL = (400, "目标充电桩排队区已满，无法换队")

    # ── 认证 ──
    INVALID_CREDENTIALS = (400, "账号或密码错误")
    LICENSE_PLATE_EXISTS = (400, "该车牌号已注册")
    TOKEN_EXPIRED = (401, "Token 已过期，请重新登录")

    # ── 计费 ──
    BILL_ALREADY_PAID = (400, "该账单已支付")
    BILL_NOT_FOUND = (404, "账单不存在")
