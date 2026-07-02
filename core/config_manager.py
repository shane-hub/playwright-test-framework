"""
配置管理模块
支持多商户 × 多环境配置加载
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from dotenv import load_dotenv

from utils.logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    """递归合并两个字典，override 的值优先"""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """
    配置管理器（单例）

    加载顺序：全局配置 → 商户配置 → 商户环境配置 → 环境变量覆盖
    使用方式：
        config = ConfigManager()                        # 全局配置（无商户）
        config = ConfigManager(merchant="merchant_1", env="staging")  # 商户+环境
    """

    _instances: Dict[str, "ConfigManager"] = {}

    def __new__(cls, merchant: Optional[str] = None, env: Optional[str] = None):
        key = f"{merchant or '_global_'}:{env or 'default'}"
        if key not in cls._instances:
            instance = super().__new__(cls)
            instance._initialized = False
            cls._instances[key] = instance
        return cls._instances[key]

    def __init__(self, merchant: Optional[str] = None, env: Optional[str] = None):
        if self._initialized:
            return
        self._merchant = merchant
        self._env = env
        self._config: Dict[str, Any] = {}
        self._load()
        self._initialized = True

    # ─── 加载逻辑 ────────────────────────────────────────────────────────────

    def _load(self) -> None:
        load_dotenv()

        # 1. 全局配置（浏览器、日志、拦截、报告等）
        global_cfg_path = _PROJECT_ROOT / "config" / "config.yaml"
        if global_cfg_path.exists():
            self._config = _load_yaml(global_cfg_path)

        # 2. 商户配置（功能矩阵 + 各环境URL）
        if self._merchant:
            merchant_path = _PROJECT_ROOT / "config" / "merchants" / f"{self._merchant}.yaml"
            if not merchant_path.exists():
                raise FileNotFoundError(
                    f"商户配置文件不存在: {merchant_path}\n"
                    f"请在 config/merchants/ 目录下创建 {self._merchant}.yaml"
                )
            merchant_cfg = _load_yaml(merchant_path)

            # 把 features / max_bet 等顶层字段合并进来
            env_specific = merchant_cfg.pop("environments", {})
            self._config = _deep_merge(self._config, merchant_cfg)

            # 3. 商户环境配置（api_url / web_url / db_host 等）
            env = self._env or self._config.get("environment", "dev")
            if env_specific and env in env_specific:
                self._config = _deep_merge(self._config, env_specific[env])
            elif env_specific:
                available = list(env_specific.keys())
                logger.warning(f"商户 {self._merchant} 无环境 '{env}'，可用: {available}")

        # 4. 环境变量覆盖（最高优先级）
        self._apply_env_overrides()

        logger.info(
            f"配置加载完成 | 商户={self._merchant or 'N/A'} | 环境={self._env or 'default'}"
        )

    def _apply_env_overrides(self) -> None:
        """环境变量优先级最高，覆盖 yaml 中的值"""
        # 通用字段
        mappings = {
            "MERCHANT":     ["merchant"],
            "ENVIRONMENT":  ["environment"],
            "API_URL":      ["api_url"],
            "WEB_URL":      ["web_url"],
            "BROWSER_TYPE": ["browser", "type"],
            "HEADLESS":     ["browser", "headless"],
            "API_TIMEOUT":  ["api", "timeout"],
        }
        for env_key, path in mappings.items():
            val = os.getenv(env_key)
            if val is not None:
                self._set(path, val)

        # 商户+环境专属账号密码
        # 命名约定：MERCHANT_1__STAGING__USERNAME（双下划线分隔）
        # ConfigManager 加载时按 self._merchant / self._env 自动读取
        if self._merchant and self._env:
            m = self._merchant.upper()   # merchant_1 → MERCHANT_1
            e = self._env.upper()        # staging    → STAGING
            username = os.getenv(f"{m}__{e}__USERNAME")
            password = os.getenv(f"{m}__{e}__PASSWORD")
            if username:
                self._set(["credentials", "username"], username)
            if password:
                self._set(["credentials", "password"], password)

    def _set(self, keys: List[str], value: Any) -> None:
        node = self._config
        for k in keys[:-1]:
            node = node.setdefault(k, {})
        last = keys[-1]
        existing = node.get(last)
        if isinstance(existing, bool):
            value = str(value).lower() in ("true", "1", "yes")
        elif isinstance(existing, int):
            value = int(value)
        node[last] = value

    # ─── 公开 API ─────────────────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        """点号路径访问，例如 config.get('browser.headless')"""
        node = self._config
        for k in key.split("."):
            if not isinstance(node, dict):
                return default
            node = node.get(k)
            if node is None:
                return default
        return node

    @property
    def merchant(self) -> Optional[str]:
        return self._merchant

    @property
    def env(self) -> Optional[str]:
        return self._env

    # ─── 功能矩阵 ─────────────────────────────────────────────────────────────

    def has_feature(self, feature: str) -> bool:
        """检查当前商户是否支持指定功能"""
        return bool(self.get(f"features.{feature}", False))

    def get_features(self) -> Dict[str, bool]:
        """返回当前商户的全部功能开关"""
        return self.get("features", {})

    # ─── 快捷属性 ─────────────────────────────────────────────────────────────

    @property
    def api_url(self) -> str:
        return self.get("api_url") or self.get("api.base_url", "")

    @property
    def web_url(self) -> str:
        return self.get("web_url", "")

    @property
    def db_host(self) -> str:
        return self.get("db_host", "localhost")

    @property
    def db_name(self) -> str:
        return self.get("db_name", "")

    def get_browser_config(self) -> Dict[str, Any]:
        return self.get("browser", {})

    def get_interception_config(self) -> Dict[str, Any]:
        return self.get("interception", {})

    def get_intercept_hosts(self) -> List[str]:
        """
        返回需要拦截的 host 列表。
        优先取 interception.hosts 配置；未配置时自动从 api_url 推断，
        这样只需填好环境 URL，不用另外维护 hosts 列表。
        """
        from urllib.parse import urlparse
        configured = self.get("interception.hosts", [])
        if configured:
            return configured
        # 从 api_url 自动推断
        if self.api_url:
            parsed = urlparse(self.api_url)
            netloc = parsed.netloc  # e.g. "api-staging.merchant1.example.com"
            if netloc:
                return [netloc]
        return []

    def get_report_config(self, report_type: str = "ui") -> Dict[str, Any]:
        return self.get(f"reports.{report_type}", {})

    def get_api_config(self) -> Dict[str, Any]:
        return self.get("api", {})

    def get_performance_config(self) -> Dict[str, Any]:
        return self.get("performance", {})

    def is_interception_enabled(self) -> bool:
        return self.get("interception.enabled", False)

    def is_headless(self) -> bool:
        return self.get("browser.headless", False)

    def get_environment(self) -> str:
        return self._env or self.get("environment", "dev")

    @classmethod
    def reset(cls) -> None:
        """清空所有单例缓存（测试间隔离用）"""
        cls._instances.clear()


# 全局默认实例（无商户，向后兼容）
config = ConfigManager()
