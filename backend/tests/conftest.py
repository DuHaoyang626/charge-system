"""
pytest 配置 — 使用临时文件 SQLite 数据库，每次测试会话自动重建。
"""

import os
import tempfile

# 使用临时文件作为测试数据库，避免文件锁冲突
_tmp_dir = tempfile.mkdtemp()
_db_path = os.path.join(_tmp_dir, "test_charge_system.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

# 此时再导入 core.database 会使用新的 URL 创建 engine
from core.database import init_db
init_db()
