"""
Logger — 统一日志基础设施服务

设计要点：
1. 所有日志写入 system_logs 表（DB 可用后）
2. 等级 >= console_threshold 的日志同时输出到终端
3. 支持双阶段初始化：DB 就绪前输出到控制台，就绪后写 DB
4. 全局单例，供全系统使用

使用方法：
    from src.utils.logger import logger
    logger.info("SYSTEM", "[启动] 系统初始化完成")
"""

import sys
from datetime import datetime
from typing import Callable, Optional

from sqlalchemy import text

from src.enums import LogLevel, LogModule


class _Logger:
    """Logger 单例实现"""

    def __init__(self):
        self._console_threshold: int = 1      # 默认：≥NOTICE 输出到终端
        self._get_session: Optional[Callable] = None  # DB session factory
        self._ready: bool = False             # DB 是否就绪

    # ── 初始化 ──────────────────────────────────────────

    def init(self, console_threshold: int, get_session: Optional[Callable] = None):
        """初始化 Logger（启动流程中调用）

        Args:
            console_threshold: 终端输出日志等级阈值
            get_session: 数据库会话工厂函数（DB 就绪后传入）
        """
        self._console_threshold = console_threshold
        if get_session:
            self._get_session = get_session
            self._ready = True

    def set_db_ready(self, get_session: Callable):
        """设置 DB 就绪（供启动流程中 DB 初始化后调用）"""
        self._get_session = get_session
        self._ready = True
        self.info(LogModule.SYSTEM, "[Logger] 数据库日志通道已开启")

    # ── 核心方法 ────────────────────────────────────────

    def log(self, module: str, level: int, detail: str):
        """记录日志：写 DB + 按条件输出终端"""
        # 输出到终端
        if level >= self._console_threshold:
            self._write_console(module, level, detail)

        # 写入数据库（仅在 DB 就绪后）
        if self._ready and self._get_session:
            try:
                self._write_db(module, level, detail)
            except Exception as e:
                self._write_console(
                    LogModule.SYSTEM, LogLevel.ERROR,
                    f"[Logger] 数据库写入失败: {e}",
                )

    # ── 便捷方法 ────────────────────────────────────────

    def info(self, module: str, detail: str):
        self.log(module, LogLevel.INFO, detail)

    def notice(self, module: str, detail: str):
        self.log(module, LogLevel.NOTICE, detail)

    def warn(self, module: str, detail: str):
        self.log(module, LogLevel.WARN, detail)

    def error(self, module: str, detail: str):
        self.log(module, LogLevel.ERROR, detail)

    def critical(self, module: str, detail: str):
        self.log(module, LogLevel.CRITICAL, detail)

    # ── 内部实现 ────────────────────────────────────────

    @staticmethod
    def _write_console(module: str, level: int, detail: str):
        """输出到终端（带颜色标记）"""
        level_names = {0: "INFO", 1: "NOTICE", 2: "WARN", 3: "ERROR", 4: "CRITICAL"}
        label = level_names.get(level, f"LVL{level}")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{label}] [{module}] {detail}", file=sys.stderr)

    def _write_db(self, module: str, level: int, detail: str):
        """写入 system_logs 表"""
        session = self._get_session()
        try:
            log_id = f"LOG{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
            session.execute(
                text("""
                    INSERT INTO system_logs (log_id, module, level, detail, created_at)
                    VALUES (:log_id, :module, :level, :detail, :created_at)
                """),
                {
                    "log_id": log_id,
                    "module": module,
                    "level": level,
                    "detail": detail,
                    "created_at": datetime.now(),
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# ── 全局单例 ───────────────────────────────────────────
logger = _Logger()
