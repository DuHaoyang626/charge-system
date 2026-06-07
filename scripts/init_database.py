"""
数据库初始化脚本

功能：创建 SQLite 数据库、建表、同步充电桩配置

用法：
    python scripts/init_database.py          # 默认路径 (data/charge_system.db)
    python scripts/init_database.py --reset  # 删除已有数据库重新创建
"""

import argparse
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.db.database import init, init_db, get_session, close
from src.db.models import ChargingPile, PileProtocol


def main():
    parser = argparse.ArgumentParser(description="初始化充电桩系统数据库")
    parser.add_argument("--reset", action="store_true", help="删除已有数据库并重建")
    args = parser.parse_args()

    # 加载配置
    config.load()
    db_path = config.system.db_path

    # 重置
    if args.reset:
        db_file = Path(db_path)
        if db_file.exists():
            db_file.unlink()
            print(f"已删除旧数据库: {db_path}")

    # 初始化
    init(db_path)
    init_db()
    print(f"数据库已创建: {db_path}")

    # 同步充电桩
    session = get_session()
    try:
        new_count = 0
        for pile_cfg in config.piles:
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
                    status="AVAILABLE",
                )
                session.add(pile)
                session.flush()

                for proto in pile_cfg.protocols:
                    session.add(PileProtocol(pile_id=pile_cfg.id, protocol=proto))
                new_count += 1

        session.commit()
        print(f"充电桩: {new_count} 新同步, {len(config.piles)} 总计")

        # 统计信息
        from sqlalchemy import text
        tables = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
        print(f"数据表: {len(tables)}")
        for t in tables:
            cnt = session.execute(
                text(f"SELECT COUNT(*) FROM [{t[0]}]")
            ).scalar()
            print(f"  {t[0]}: {cnt} 行")
    finally:
        session.close()
        close()


if __name__ == "__main__":
    main()
