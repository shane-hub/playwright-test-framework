"""
请求拦截器模块
负责拦截 Playwright 页面的网络请求并记录
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from playwright.async_api import Page, Route, Request, Response

from utils.logger import get_logger
from utils.helpers import ensure_dir, get_timestamp, save_json

logger = get_logger(__name__)


class RequestInterceptor:
    """请求拦截器"""
    
    def __init__(self, hosts: List[str], save_dir: str = "data/requests",
                 deduplicate: bool = True, ignore_resource_types: Optional[List[str]] = None):
        """
        初始化请求拦截器
        
        Args:
            hosts: 需要拦截的 host 列表
            save_dir: 保存请求数据的目录
            deduplicate: 是否去重相似请求
            ignore_resource_types: 忽略的资源类型列表
        """
        self.hosts = hosts
        self.save_dir = Path(save_dir)
        self.deduplicate = deduplicate
        self.ignore_resource_types = ignore_resource_types or []
        self.intercepted_requests: List[Dict[str, Any]] = []
        self._request_signatures = set()  # 用于去重
        
        ensure_dir(self.save_dir)
        logger.info(f"请求拦截器初始化完成,监听 hosts: {hosts}")
    
    def _should_intercept(self, request: Request) -> bool:
        """
        判断是否应该拦截该请求
        
        Args:
            request: Playwright 请求对象
            
        Returns:
            bool: 是否拦截
        """
        # 检查资源类型
        if request.resource_type in self.ignore_resource_types:
            return False
        
        # 检查 host
        url = request.url
        for host in self.hosts:
            if host in url:
                return True
        
        return False
    
    def _generate_signature(self, request: Request) -> str:
        """
        生成请求签名用于去重
        
        Args:
            request: Playwright 请求对象
            
        Returns:
            str: 请求签名
        """
        method = request.method
        url = request.url.split('?')[0]  # 去除查询参数
        return f"{method}:{url}"
    
    async def _handle_route(self, route: Route) -> None:
        """
        处理路由拦截
        
        Args:
            route: Playwright 路由对象
        """
        request = route.request
        
        if not self._should_intercept(request):
            await route.continue_()
            return
        
        # 去重检查
        if self.deduplicate:
            signature = self._generate_signature(request)
            if signature in self._request_signatures:
                logger.debug(f"跳过重复请求: {signature}")
                await route.continue_()
                return
            self._request_signatures.add(signature)
        
        # 记录请求信息
        request_data = {
            'timestamp': datetime.now().isoformat(),
            'method': request.method,
            'url': request.url,
            'headers': dict(request.headers),
            'resource_type': request.resource_type,
        }
        
        # 记录请求体
        try:
            post_data = request.post_data
            if post_data:
                try:
                    request_data['body'] = json.loads(post_data)
                except json.JSONDecodeError:
                    request_data['body'] = post_data
        except Exception as e:
            logger.debug(f"无法获取请求体: {e}")
        
        # 继续请求并获取响应
        try:
            response = await route.fetch()
            
            # 记录响应信息
            request_data['response'] = {
                'status': response.status,
                'status_text': response.status_text,
                'headers': dict(response.headers),
            }
            
            # 记录响应体
            try:
                body = await response.body()
                try:
                    request_data['response']['body'] = json.loads(body.decode('utf-8'))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_data['response']['body'] = body.decode('utf-8', errors='ignore')
            except Exception as e:
                logger.debug(f"无法获取响应体: {e}")
            
            # 保存请求数据
            self.intercepted_requests.append(request_data)
            logger.info(f"拦截请求: {request.method} {request.url} -> {response.status}")
            
            # 继续响应
            await route.fulfill(
                response=response,
                headers=response.headers
            )
            
        except Exception as e:
            logger.error(f"处理请求时出错: {e}")
            await route.continue_()
    
    async def setup(self, page: Page) -> None:
        """
        为页面设置请求拦截
        
        Args:
            page: Playwright 页面对象
        """
        await page.route("**/*", self._handle_route)
        logger.info("请求拦截已启用")
    
    def get_requests(self) -> List[Dict[str, Any]]:
        """
        获取拦截的请求列表
        
        Returns:
            List[Dict]: 请求数据列表
        """
        return self.intercepted_requests
    
    def save_requests(self, filename: Optional[str] = None) -> str:
        """
        保存拦截的请求到文件
        
        Args:
            filename: 文件名,不指定则使用时间戳
            
        Returns:
            str: 保存的文件路径
        """
        if not filename:
            filename = f"requests_{get_timestamp()}.json"
        
        filepath = self.save_dir / filename
        save_json({
            'total': len(self.intercepted_requests),
            'timestamp': datetime.now().isoformat(),
            'hosts': self.hosts,
            'requests': self.intercepted_requests
        }, filepath)
        
        logger.info(f"已保存 {len(self.intercepted_requests)} 个请求到: {filepath}")
        return str(filepath)
    
    def clear(self) -> None:
        """清空拦截的请求"""
        self.intercepted_requests.clear()
        self._request_signatures.clear()
        logger.info("已清空拦截的请求")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取拦截请求的摘要信息
        
        Returns:
            Dict: 摘要信息
        """
        methods = {}
        status_codes = {}
        
        for req in self.intercepted_requests:
            # 统计方法
            method = req['method']
            methods[method] = methods.get(method, 0) + 1
            
            # 统计状态码
            if 'response' in req:
                status = req['response']['status']
                status_codes[status] = status_codes.get(status, 0) + 1
        
        return {
            'total_requests': len(self.intercepted_requests),
            'methods': methods,
            'status_codes': status_codes,
            'hosts': self.hosts
        }
