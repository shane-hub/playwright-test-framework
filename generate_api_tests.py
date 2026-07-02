#!/usr/bin/env python
"""
CLI 工具 - 第三层：YAML 测试用例 → pytest 脚本

用法：
  # 生成目录下所有 yaml
  python generate_api_tests.py tests/api/cases/

  # 生成单个 yaml
  python generate_api_tests.py tests/api/cases/post_api_v1_login.yaml

  # 指定输出目录
  python generate_api_tests.py tests/api/cases/ --output-dir tests/api/generated
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.api_generator import APITestGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从 YAML case 文件生成 pytest 脚本（第三层）"
    )
    parser.add_argument(
        "input",
        help="YAML 文件路径 或 包含 .yaml 文件的目录",
    )
    parser.add_argument(
        "--output-dir", "-d",
        default="tests/api/generated",
        help="pytest 脚本输出目录（默认: tests/api/generated）",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"路径不存在: {input_path}")
        sys.exit(1)

    gen = APITestGenerator(output_dir=args.output_dir)

    try:
        if input_path.is_dir():
            files = gen.generate_from_yaml_dir(input_path)
        else:
            result = gen.generate_from_yaml_file(input_path)
            files = [result] if result else []

        if files:
            print(f"\n✅ 生成 {len(files)} 个测试文件:")
            for f in files:
                print(f"   {f}")
            print(f"\n运行测试：pytest {args.output_dir} --merchant=<商户> --env=<环境>")
        else:
            print("⚠️  未生成任何文件")

    except Exception as exc:
        logger.error(f"生成失败: {exc}")
        raise


if __name__ == "__main__":
    main()
