"""
API 变化检测器
检测拦截的请求是否有新增或变动
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set, Tuple

from utils.logger import get_logger
from utils.helpers import load_json

logger = get_logger(__name__)


class APIChangeDetector:
    """API 变化检测器"""
    
    def __init__(self, cache_file: str = "data/.api_cache.json"):
        """
        初始化检测器
        
        Args:
            cache_file: API 缓存文件路径
        """
        self.cache_file = Path(cache_file)
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cached_apis = self._load_cache()
    
    def _load_cache(self) -> Dict[str, str]:
        """
        加载 API 缓存
        
        Returns:
            Dict: API 签名缓存 {signature: hash}
        """
        if self.cache_file.exists():
            try:
                return load_json(self.cache_file)
            except Exception as e:
                logger.warning(f"加载 API 缓存失败: {e}")
        return {}
    
    def _save_cache(self) -> None:
        """保存 API 缓存"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cached_apis, f, indent=2, ensure_ascii=False)
            logger.debug(f"API 缓存已保存: {self.cache_file}")
        except Exception as e:
            logger.error(f"保存 API 缓存失败: {e}")
    
    def _generate_api_signature(self, request: Dict[str, Any]) -> str:
        """
        生成 API 签名
        
        Args:
            request: 请求数据
            
        Returns:
            str: API 签名 (method:url_path)
        """
        method = request.get('method', 'GET')
        url = request.get('url', '')
        
        # 提取 URL 路径(去除查询参数和域名)
        from urllib.parse import urlparse
        parsed = urlparse(url)
        path = parsed.path
        
        return f"{method}:{path}"
    
    def _generate_request_hash(self, request: Dict[str, Any]) -> str:
        """
        生成请求的哈希值(用于检测变化)
        
        Args:
            request: 请求数据
            
        Returns:
            str: 请求哈希值
        """
        # 提取关键信息用于哈希
        key_info = {
            'method': request.get('method'),
            'url': request.get('url', '').split('?')[0],  # 去除查询参数
            'body_keys': list(request.get('body', {}).keys()) if isinstance(request.get('body'), dict) else None,
            'response_status': request.get('response', {}).get('status'),
        }
        
        # 生成哈希
        info_str = json.dumps(key_info, sort_keys=True)
        return hashlib.md5(info_str.encode()).hexdigest()
    
    def detect_changes(self, requests: List[Dict[str, Any]]) -> Tuple[List[Dict], List[Dict], bool]:
        """
        检测 API 变化
        
        Args:
            requests: 新拦截的请求列表
            
        Returns:
            Tuple: (新增的请求, 变化的请求, 是否有变化)
        """
        new_requests = []
        changed_requests = []
        current_signatures = {}
        
        for request in requests:
            signature = self._generate_api_signature(request)
            request_hash = self._generate_request_hash(request)
            
            current_signatures[signature] = request_hash
            
            if signature not in self.cached_apis:
                # 新增的 API
                new_requests.append(request)
                logger.info(f"检测到新 API: {signature}")
            elif self.cached_apis[signature] != request_hash:
                # API 有变化
                changed_requests.append(request)
                logger.info(f"检测到 API 变化: {signature}")
        
        has_changes = len(new_requests) > 0 or len(changed_requests) > 0
        
        if has_changes:
            # 更新缓存
            self.cached_apis.update(current_signatures)
            self._save_cache()
        
        return new_requests, changed_requests, has_changes
    
    def get_summary(self, new_requests: List[Dict], changed_requests: List[Dict]) -> str:
        """
        获取变化摘要
        
        Args:
            new_requests: 新增的请求
            changed_requests: 变化的请求
            
        Returns:
            str: 摘要信息
        """
        summary_lines = []
        
        if new_requests:
            summary_lines.append(f"🆕 新增 API: {len(new_requests)} 个")
            for req in new_requests[:5]:  # 只显示前5个
                sig = self._generate_api_signature(req)
                summary_lines.append(f"   - {sig}")
            if len(new_requests) > 5:
                summary_lines.append(f"   ... 还有 {len(new_requests) - 5} 个")
        
        if changed_requests:
            summary_lines.append(f"🔄 变化的 API: {len(changed_requests)} 个")
            for req in changed_requests[:5]:
                sig = self._generate_api_signature(req)
                summary_lines.append(f"   - {sig}")
            if len(changed_requests) > 5:
                summary_lines.append(f"   ... 还有 {len(changed_requests) - 5} 个")
        
        return '\n'.join(summary_lines) if summary_lines else "✅ 没有 API 变化"
    
    def clear_cache(self) -> None:
        """清空缓存"""
        self.cached_apis = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("API 缓存已清空")
