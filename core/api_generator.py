"""
API 测试用例生成器
从拦截的请求自动生成 API 测试用例
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from utils.logger import get_logger
from utils.helpers import load_json, ensure_dir, get_timestamp

logger = get_logger(__name__)


class APITestGenerator:
    """API 测试用例生成器"""
    
    def __init__(self, output_dir: str = "tests/api/generated"):
        """
        初始化生成器
        
        Args:
            output_dir: 生成的测试用例输出目录
        """
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)
        logger.info(f"API 测试生成器初始化完成,输出目录: {output_dir}")
    
    def _sanitize_name(self, name: str) -> str:
        """
        清理名称,使其符合 Python 命名规范
        
        Args:
            name: 原始名称
            
        Returns:
            str: 清理后的名称
        """
        # 移除特殊字符,替换为下划线
        sanitized = ''.join(c if c.isalnum() or c == '_' else '_' for c in name)
        # 移除连续的下划线
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        # 移除首尾下划线
        sanitized = sanitized.strip('_')
        # 确保以字母开头
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'test_' + sanitized
        return sanitized.lower()
    
    def _extract_test_name(self, request_data: Dict[str, Any]) -> str:
        """
        从请求数据提取测试用例名称
        
        Args:
            request_data: 请求数据
            
        Returns:
            str: 测试用例名称
        """
        method = request_data['method'].lower()
        url = request_data['url']
        
        # 提取路径
        path = url.split('?')[0].split('/')[-1] or 'root'
        
        return f"test_{method}_{self._sanitize_name(path)}"
    
    def _generate_test_function(self, request_data: Dict[str, Any], index: int) -> str:
        """
        生成单个测试函数代码
        
        Args:
            request_data: 请求数据
            index: 请求索引
            
        Returns:
            str: 测试函数代码
        """
        method = request_data['method']
        url = request_data['url']
        headers = request_data.get('headers', {})
        body = request_data.get('body')
        response = request_data.get('response', {})
        
        test_name = self._extract_test_name(request_data)
        if index > 0:
            test_name = f"{test_name}_{index}"
        
        # 生成测试函数
        code_lines = [
            f"def {test_name}(api_client):",
            f'    """',
            f'    测试: {method} {url}',
            f'    自动生成于: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'    """',
        ]
        
        # 准备请求参数
        if body:
            body_str = json.dumps(body, indent=8, ensure_ascii=False)
            code_lines.append(f"    data = {body_str}")
        else:
            code_lines.append(f"    data = None")
        
        # 准备 headers
        if headers:
            # 过滤掉一些自动生成的 headers
            filtered_headers = {k: v for k, v in headers.items() 
                              if k.lower() not in ['host', 'content-length', 'connection']}
            if filtered_headers:
                headers_str = json.dumps(filtered_headers, indent=8, ensure_ascii=False)
                code_lines.append(f"    headers = {headers_str}")
            else:
                code_lines.append(f"    headers = None")
        else:
            code_lines.append(f"    headers = None")
        
        # 发送请求
        code_lines.extend([
            f"    ",
            f"    # 发送请求",
            f'    response = api_client.send_request(',
            f'        method="{method}",',
            f'        url="{url}",',
            f'        json=data,',
            f'        headers=headers',
            f'    )',
        ])
        
        # 添加断言
        code_lines.extend([
            f"    ",
            f"    # 断言",
        ])
        
        if 'status' in response:
            status = response['status']
            code_lines.append(f"    api_client.assert_status_code(response, {status})")
        
        # 添加响应时间断言
        code_lines.append(f"    api_client.assert_response_time(response, max_time=3000)")
        
        # 如果响应是 JSON,添加 JSON 断言
        if 'body' in response and isinstance(response['body'], dict):
            code_lines.append(f"    assert response.json() is not None")
        
        return '\n'.join(code_lines)
    
    def generate_from_file(self, requests_file: str, output_file: Optional[str] = None) -> str:
        """
        从请求文件生成测试用例
        
        Args:
            requests_file: 请求数据文件路径
            output_file: 输出文件名,不指定则使用时间戳
            
        Returns:
            str: 生成的测试文件路径
        """
        # 加载请求数据
        data = load_json(requests_file)
        requests = data.get('requests', [])
        
        if not requests:
            logger.warning(f"请求文件中没有请求数据: {requests_file}")
            return ""
        
        logger.info(f"从 {requests_file} 加载了 {len(requests)} 个请求")
        
        # 生成测试代码
        test_code = self._generate_test_file(requests)
        
        # 保存测试文件
        if not output_file:
            output_file = f"test_generated_{get_timestamp()}.py"
        
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info(f"已生成测试文件: {output_path}")
        return str(output_path)
    
    def _generate_test_file(self, requests: List[Dict[str, Any]]) -> str:
        """
        生成完整的测试文件代码
        
        Args:
            requests: 请求数据列表
            
        Returns:
            str: 测试文件代码
        """
        # 文件头部
        header = [
            '"""',
            'API 测试用例 - 自动生成',
            f'生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'请求数量: {len(requests)}',
            '"""',
            'import pytest',
            '',
            ''
        ]
        
        # 生成测试函数
        test_functions = []
        test_name_counts = {}
        
        for request_data in requests:
            base_name = self._extract_test_name(request_data)
            count = test_name_counts.get(base_name, 0)
            test_name_counts[base_name] = count + 1
            
            test_func = self._generate_test_function(request_data, count)
            test_functions.append(test_func)
        
        # 组合代码
        code = '\n'.join(header) + '\n\n'.join(test_functions)
        return code
    
    def generate_from_requests(self, requests: List[Dict[str, Any]], 
                              output_file: Optional[str] = None) -> str:
        """
        直接从请求列表生成测试用例
        
        Args:
            requests: 请求数据列表
            output_file: 输出文件名
            
        Returns:
            str: 生成的测试文件路径
        """
        if not requests:
            logger.warning("请求列表为空")
            return ""
        
        # 生成测试代码
        test_code = self._generate_test_file(requests)
        
        # 保存测试文件
        if not output_file:
            output_file = f"test_generated_{get_timestamp()}.py"
        
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(test_code)
        
        logger.info(f"已生成测试文件: {output_path} (包含 {len(requests)} 个测试)")
        return str(output_path)
