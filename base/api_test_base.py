"""
API 测试基类
提供 API 测试的基础功能
"""
import time
import requests
from typing import Dict, Any, Optional, Union
from jsonschema import validate, ValidationError

from core.config_manager import config
from utils.logger import get_logger

logger = get_logger(__name__)


class APITestBase:
    """API 测试基类"""
    
    def __init__(self):
        """初始化 API 测试基类"""
        self.api_config = config.get_api_config()
        self.base_url = self.api_config.get('base_url', '')
        self.timeout = self.api_config.get('timeout', 30)
        self.session = requests.Session()
        
        # 设置默认 headers
        default_headers = self.api_config.get('headers', {})
        self.session.headers.update(default_headers)
        
        logger.info(f"API 测试基类初始化完成,base_url: {self.base_url}")
    
    def setup_method(self):
        """测试方法设置"""
        logger.info("开始 API 测试")
    
    def teardown_method(self):
        """测试方法清理"""
        logger.info("API 测试结束")
    
    def send_request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        发送 HTTP 请求
        
        Args:
            method: HTTP 方法 (GET, POST, PUT, DELETE, etc.)
            url: 请求 URL (可以是完整 URL 或相对路径)
            **kwargs: requests 库的其他参数
            
        Returns:
            requests.Response: 响应对象
        """
        # 如果是相对路径,添加 base_url
        if not url.startswith('http'):
            url = self.base_url.rstrip('/') + '/' + url.lstrip('/')
        
        # 设置超时
        if 'timeout' not in kwargs:
            kwargs['timeout'] = self.timeout
        
        # 记录请求
        logger.info(f"发送请求: {method} {url}")
        if 'json' in kwargs:
            logger.debug(f"请求体: {kwargs['json']}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 发送请求
        try:
            response = self.session.request(method, url, **kwargs)
            
            # 记录响应时间
            response_time = (time.time() - start_time) * 1000  # 转换为毫秒
            response.elapsed_ms = response_time
            
            logger.info(f"响应: {response.status_code} (耗时: {response_time:.2f}ms)")
            logger.debug(f"响应体: {response.text[:500]}")  # 只记录前500字符
            
            return response
            
        except requests.RequestException as e:
            logger.error(f"请求失败: {e}")
            raise
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET 请求"""
        return self.send_request('GET', url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST 请求"""
        return self.send_request('POST', url, **kwargs)
    
    def put(self, url: str, **kwargs) -> requests.Response:
        """PUT 请求"""
        return self.send_request('PUT', url, **kwargs)
    
    def delete(self, url: str, **kwargs) -> requests.Response:
        """DELETE 请求"""
        return self.send_request('DELETE', url, **kwargs)
    
    def patch(self, url: str, **kwargs) -> requests.Response:
        """PATCH 请求"""
        return self.send_request('PATCH', url, **kwargs)
    
    # 断言方法
    
    def assert_status_code(self, response: requests.Response, expected_code: int) -> None:
        """
        断言状态码
        
        Args:
            response: 响应对象
            expected_code: 期望的状态码
        """
        actual_code = response.status_code
        assert actual_code == expected_code, \
            f"状态码不匹配: 期望 {expected_code}, 实际 {actual_code}"
        logger.debug(f"状态码断言通过: {expected_code}")
    
    def assert_response_time(self, response: requests.Response, max_time: int) -> None:
        """
        断言响应时间
        
        Args:
            response: 响应对象
            max_time: 最大响应时间(毫秒)
        """
        actual_time = getattr(response, 'elapsed_ms', response.elapsed.total_seconds() * 1000)
        assert actual_time <= max_time, \
            f"响应时间超时: 期望 <={max_time}ms, 实际 {actual_time:.2f}ms"
        logger.debug(f"响应时间断言通过: {actual_time:.2f}ms <= {max_time}ms")
    
    def assert_json_schema(self, response: requests.Response, schema: Dict[str, Any]) -> None:
        """
        断言 JSON schema
        
        Args:
            response: 响应对象
            schema: JSON schema 定义
        """
        try:
            json_data = response.json()
            validate(instance=json_data, schema=schema)
            logger.debug("JSON schema 断言通过")
        except ValidationError as e:
            raise AssertionError(f"JSON schema 验证失败: {e.message}")
    
    def assert_json_contains(self, response: requests.Response, 
                            expected_data: Dict[str, Any]) -> None:
        """
        断言响应 JSON 包含指定的键值对
        
        Args:
            response: 响应对象
            expected_data: 期望包含的数据
        """
        json_data = response.json()
        
        for key, expected_value in expected_data.items():
            assert key in json_data, f"响应中缺少键: {key}"
            actual_value = json_data[key]
            assert actual_value == expected_value, \
                f"键 '{key}' 的值不匹配: 期望 {expected_value}, 实际 {actual_value}"
        
        logger.debug(f"JSON 包含断言通过: {expected_data}")
    
    def assert_header_exists(self, response: requests.Response, header_name: str) -> None:
        """
        断言响应头存在
        
        Args:
            response: 响应对象
            header_name: 响应头名称
        """
        assert header_name in response.headers, \
            f"响应头中缺少: {header_name}"
        logger.debug(f"响应头断言通过: {header_name}")
    
    def assert_header_value(self, response: requests.Response, 
                           header_name: str, expected_value: str) -> None:
        """
        断言响应头的值
        
        Args:
            response: 响应对象
            header_name: 响应头名称
            expected_value: 期望的值
        """
        self.assert_header_exists(response, header_name)
        actual_value = response.headers[header_name]
        assert actual_value == expected_value, \
            f"响应头 '{header_name}' 的值不匹配: 期望 {expected_value}, 实际 {actual_value}"
        logger.debug(f"响应头值断言通过: {header_name}={expected_value}")
    
    def assert_contains_text(self, response: requests.Response, text: str) -> None:
        """
        断言响应体包含指定文本
        
        Args:
            response: 响应对象
            text: 期望包含的文本
        """
        assert text in response.text, \
            f"响应体中不包含文本: {text}"
        logger.debug(f"文本包含断言通过: {text}")
