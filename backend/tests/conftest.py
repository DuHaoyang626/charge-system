"""
pytest 配置 — 每次测试会话开始时重置数据库。
确保测试环境干净，不受之前运行的残留数据影响。
"""

import os
from pathlib import Path

# 确保 data/ 目录存在
_data_dir = Path(__file__).resolve().parent.parent / "data"
_data_dir.mkdir(parents=True, exist_ok=True)

# 尝试删除旧数据库（可能被其他进程锁定）
import time
_db_path = _data_dir / "charge_system.db"
if _db_path.exists():
    for _ in range(3):
        try:
            _db_path.unlink()
            break
        except PermissionError:
            time.sleep(0.5)
    else:
        print(f"[conftest] 无法删除旧数据库 {_db_path}，将尝试覆盖初始化")

from core.database import init_db
init_db()
