#!/usr/bin/env python
"""
命令行工具 - 从拦截的请求生成 API 测试用例
"""
import argparse
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.api_generator import APITestGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='从拦截的请求生成 API 测试用例'
    )
    parser.add_argument(
        'input_file',
        help='拦截的请求数据文件路径'
    )
    parser.add_argument(
        '-o', '--output',
        help='输出文件名(可选)',
        default=None
    )
    parser.add_argument(
        '-d', '--output-dir',
        help='输出目录',
        default='tests/api/generated'
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    input_file = Path(args.input_file)
    if not input_file.exists():
        logger.error(f"输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 生成测试用例
    try:
        generator = APITestGenerator(output_dir=args.output_dir)
        output_path = generator.generate_from_file(
            str(input_file),
            output_file=args.output
        )
        
        print(f"✅ 成功生成测试文件: {output_path}")
        
    except Exception as e:
        logger.error(f"生成测试用例失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
