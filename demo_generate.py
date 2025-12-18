"""
示例:从拦截的请求生成并运行 API 测试的完整流程
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.api_generator import APITestGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


def demo_generate_api_tests():
    """演示如何生成 API 测试用例"""
    
    # 模拟拦截的请求数据
    sample_requests = [
        {
            "timestamp": "2023-12-17T10:00:00",
            "method": "GET",
            "url": "https://jsonplaceholder.typicode.com/users/1",
            "headers": {"Content-Type": "application/json"},
            "response": {
                "status": 200,
                "body": {"id": 1, "name": "Leanne Graham"}
            }
        },
        {
            "timestamp": "2023-12-17T10:01:00",
            "method": "POST",
            "url": "https://jsonplaceholder.typicode.com/posts",
            "headers": {"Content-Type": "application/json"},
            "body": {"title": "Test Post", "body": "Content", "userId": 1},
            "response": {
                "status": 201,
                "body": {"id": 101, "title": "Test Post"}
            }
        }
    ]
    
    # 创建生成器
    generator = APITestGenerator(output_dir="tests/api/generated")
    
    # 生成测试用例
    output_file = generator.generate_from_requests(
        sample_requests,
        output_file="test_demo_generated.py"
    )
    
    logger.info(f"✅ 生成的测试文件: {output_file}")
    logger.info("💡 运行生成的测试: pytest tests/api/generated/test_demo_generated.py -v")
    
    return output_file


if __name__ == "__main__":
    print("=" * 60)
    print("API 测试生成器演示")
    print("=" * 60)
    
    output_file = demo_generate_api_tests()
    
    print("\n" + "=" * 60)
    print("✅ 演示完成!")
    print("=" * 60)
    print(f"\n生成的测试文件: {output_file}")
    print("\n下一步:")
    print("1. 查看生成的测试文件")
    print("2. 运行测试: pytest tests/api/generated/test_demo_generated.py -v")
    print("=" * 60)
