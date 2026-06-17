"""
系统日志模块 — 同时写入 SQLite 数据库 + 终端输出。

用法：
    from core.logger import system_logger

    system_logger.info("module_name", "事件描述")
    system_logger.warning("module_name", "警告描述")
    system_logger.error("module_name", "错误描述")

等级过滤（终端输出）：
    system_logger.set_level(logging.WARNING)  # 只显示 WARNING 及以上
    或通过 python main.py --log_level warning 启动时设置。

数据库写入静默失败，不影响主流程。
"""

import logging
import threading
from datetime import datetime
from queue import Queue

from sqlmodel import Session

# ── ANSI 颜色 ──
_RESET = "\033[0m"
_BOLD = "\033[1m"
_COLORS = {
    "INFO": "\033[36m",      # 青色
    "WARNING": "\033[33m",   # 黄色
    "ERROR": "\033[31m",     # 红色
}

_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

_REVERSE_LEVEL_MAP = {
    logging.DEBUG: "DEBUG",
    logging.INFO: "INFO",
    logging.WARNING: "WARNING",
    logging.ERROR: "ERROR",
}


class SystemLogger:
    """
    系统日志器 — 同时写数据库和终端。

    数据库写入通过后台线程队列异步执行，不阻塞调用方。
    """

    def __init__(self):
        self._level = logging.INFO
        self._queue: Queue[tuple[str, str, str, datetime]] = Queue()
        self._worker = threading.Thread(target=self._worker_loop, daemon=True, name="log-writer")
        self._worker.start()

    # ── 等级管理 ──

    def set_level(self, level: int | str) -> None:
        """设置终端输出过滤等级。"""
        if isinstance(level, str):
            level = _LEVEL_MAP.get(level.lower(), logging.INFO)
        self._level = level

    def get_level_name(self) -> str:
        """返回当前等级的字符串表示。"""
        return _REVERSE_LEVEL_MAP.get(self._level, "INFO")

    # ── 公开日志方法 ──

    def info(self, module: str, content: str) -> None:
        """记录一条 INFO 日志。"""
        self._log(logging.INFO, "INFO", module, content)

    def warning(self, module: str, content: str) -> None:
        """记录一条 WARNING 日志。"""
        self._log(logging.WARNING, "WARNING", module, content)

    def error(self, module: str, content: str) -> None:
        """记录一条 ERROR 日志。"""
        self._log(logging.ERROR, "ERROR", module, content)

    # ── 内部方法 ──

    def _log(self, level_num: int, level_name: str, module: str, content: str) -> None:
        now = datetime.utcnow()

        # 终端输出（带颜色和等级过滤）
        if level_num >= self._level:
            color = _COLORS.get(level_name, _RESET)
            if level_num >= logging.ERROR:
                tag = f"{_BOLD}{color}[{level_name}]{_RESET}"
            else:
                tag = f"{color}[{level_name}]{_RESET}"
            print(
                f"{color}[{now.isoformat()}]{_RESET} "
                f"{tag} "
                f"{color}[{module}]{_RESET} "
                f"{content}"
            )

        # 放入异步队列写数据库
        self._queue.put((level_name, module, content, now))

    def _worker_loop(self) -> None:
        """后台线程：从队列取出日志条目写入 SQLite。"""
        # 延迟导入避免与 core.database 的循环依赖
        from core.database import engine
        from model.log_record import LogRecord

        while True:
            level_name, module, content, created_at = self._queue.get()
            try:
                with Session(engine) as db:
                    db.add(LogRecord(
                        level=level_name,
                        module=module,
                        content=content,
                        created_at=created_at,
                    ))
                    db.commit()
            except Exception:
                pass  # 日志写入失败不应影响系统运行
            finally:
                self._queue.task_done()


# ── 全局单例 ──
system_logger = SystemLogger()
