"""
辅助工具函数
"""
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Union
from datetime import datetime


def load_json(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载 JSON 文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict: JSON 数据
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Union[str, Path], indent: int = 2) -> None:
    """
    保存数据为 JSON 文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
        indent: 缩进空格数
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def load_yaml(file_path: Union[str, Path]) -> Dict[str, Any]:
    """
    加载 YAML 文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict: YAML 数据
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], file_path: Union[str, Path]) -> None:
    """
    保存数据为 YAML 文件
    
    Args:
        data: 要保存的数据
        file_path: 文件路径
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def get_timestamp(format_str: str = "%Y%m%d_%H%M%S") -> str:
    """
    获取当前时间戳字符串
    
    Args:
        format_str: 时间格式字符串
        
    Returns:
        str: 格式化的时间戳
    """
    return datetime.now().strftime(format_str)


def ensure_dir(dir_path: Union[str, Path]) -> Path:
    """
    确保目录存在,不存在则创建
    
    Args:
        dir_path: 目录路径
        
    Returns:
        Path: 目录路径对象
    """
    path = Path(dir_path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """
    深度合并两个字典
    
    Args:
        dict1: 第一个字典
        dict2: 第二个字典(优先级更高)
        
    Returns:
        Dict: 合并后的字典
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result
