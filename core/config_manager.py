"""
配置管理模块
负责加载和管理测试框架的配置
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

from utils.helpers import load_yaml, deep_merge
from utils.logger import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """配置管理器"""
    
    _instance = None
    _config = None
    
    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化配置管理器"""
        if self._config is None:
            self._load_config()
    
    def _load_config(self) -> None:
        """加载配置文件"""
        # 加载环境变量
        load_dotenv()
        
        # 获取项目根目录
        project_root = Path(__file__).parent.parent
        config_file = project_root / "config" / "config.yaml"
        
        if not config_file.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        # 加载 YAML 配置
        self._config = load_yaml(config_file)
        
        # 环境变量覆盖配置
        self._override_from_env()
        
        logger.info(f"配置加载成功: {config_file}")
    
    def _override_from_env(self) -> None:
        """使用环境变量覆盖配置"""
        env_mappings = {
            'ENVIRONMENT': ['environment'],
            'BROWSER_TYPE': ['browser', 'type'],
            'HEADLESS': ['browser', 'headless'],
            'API_BASE_URL': ['api', 'base_url'],
            'API_TIMEOUT': ['api', 'timeout'],
        }
        
        for env_key, config_path in env_mappings.items():
            env_value = os.getenv(env_key)
            if env_value is not None:
                self._set_nested_value(config_path, env_value)
    
    def _set_nested_value(self, keys: List[str], value: Any) -> None:
        """设置嵌套配置值"""
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # 类型转换
        if isinstance(current.get(keys[-1]), bool):
            value = value.lower() in ('true', '1', 'yes')
        elif isinstance(current.get(keys[-1]), int):
            value = int(value)
        
        current[keys[-1]] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值,支持点号分隔的嵌套键
        
        Args:
            key: 配置键,支持 "browser.type" 格式
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_browser_config(self) -> Dict[str, Any]:
        """获取浏览器配置"""
        return self.get('browser', {})
    
    def get_interception_config(self) -> Dict[str, Any]:
        """获取拦截配置"""
        return self.get('interception', {})
    
    def get_intercept_hosts(self) -> List[str]:
        """获取需要拦截的 host 列表"""
        return self.get('interception.hosts', [])
    
    def get_report_config(self, report_type: str = 'ui') -> Dict[str, Any]:
        """
        获取报告配置
        
        Args:
            report_type: 报告类型 ('ui' 或 'api')
            
        Returns:
            报告配置字典
        """
        return self.get(f'reports.{report_type}', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取 API 配置"""
        return self.get('api', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.get('logging', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """获取性能监控配置"""
        return self.get('performance', {})
    
    def is_interception_enabled(self) -> bool:
        """检查是否启用请求拦截"""
        return self.get('interception.enabled', False)
    
    def is_headless(self) -> bool:
        """检查是否为无头模式"""
        return self.get('browser.headless', False)
    
    def get_environment(self) -> str:
        """获取当前环境"""
        return self.get('environment', 'test')
    
    def reload(self) -> None:
        """重新加载配置"""
        self._config = None
        self._load_config()


# 全局配置实例
config = ConfigManager()
