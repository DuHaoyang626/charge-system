"""
配置加载 — 从 .env 文件读取基础设施配置。

使用方式：
    from core.config import settings
    settings.JWT_SECRET_KEY
    settings.DATABASE_URL
"""

import os
from pathlib import Path


def _load_env_file(env_path: Path) -> None:
    """简易 .env 文件加载器，无需 python-dotenv 依赖。"""
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'").strip()
            if key and key not in os.environ:
                os.environ[key] = value


# 加载 .env 文件（项目根目录）
_env_path = Path(__file__).resolve().parent.parent / ".env"
_load_env_file(_env_path)


class _Settings:
    """应用配置，从环境变量读取，带默认值兜底。"""

    # ── JWT ──
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY", "change-this-to-a-random-string-at-least-32-chars"
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_DAYS: int = 1

    # ── 数据库 ──
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "sqlite:///./data/charge_system.db"
    )

    # ── 调度循环 ──
    DISPATCH_INTERVAL_SECONDS: int = 10
    STARTUP_DELAY_SECONDS: int = 2


settings = _Settings()
