"""
ConfigLoader — 配置加载器

职责：
1. 系统启动时读取 config/application.yml
2. 验证 YAML 结构并转为类型安全的 AppSettings 对象
3. 提供全局单例访问（也可注入到服务构造函数）
4. 支持运行中重载（reload）

使用方法：
    from src.config.loader import config
    config.billing.default_prices.peak_price  # 1.2
"""

from pathlib import Path
from typing import Optional

import yaml

from src.config.settings import AppSettings


class ConfigLoader:
    """配置加载器（单例模式）"""

    _instance: Optional["ConfigLoader"] = None
    _settings: Optional[AppSettings] = None
    _config_path: Path = Path("config/application.yml")

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, path: Optional[Path] = None) -> AppSettings:
        """读取并解析 application.yml"""
        if path:
            self._config_path = path

        if not self._config_path.exists():
            raise FileNotFoundError(
                f"配置文件不存在: {self._config_path.resolve()}"
            )

        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw:
            raise ValueError("配置文件为空")

        self._settings = AppSettings(**raw)
        return self._settings

    def reload(self) -> AppSettings:
        """运行时重载配置（管理员修改配置后调用）"""
        return self.load()

    @property
    def settings(self) -> AppSettings:
        if self._settings is None:
            raise RuntimeError("配置尚未加载，请先调用 loader.load()")
        return self._settings

    # ── 便捷属性（直接访问常用配置） ─────────────────

    @property
    def station(self):
        return self.settings.station

    @property
    def piles(self):
        return self.settings.piles

    @property
    def dispatch(self):
        return self.settings.dispatch

    @property
    def billing(self):
        return self.settings.billing

    @property
    def monitoring(self):
        return self.settings.monitoring

    @property
    def logging(self):
        return self.settings.logging

    @property
    def system(self):
        return self.settings.system


# ── 全局单例（导入即用） ──────────────────────────────
config = ConfigLoader()
