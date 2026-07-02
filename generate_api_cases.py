#!/usr/bin/env python
"""
CLI 工具 - 第二层：拦截 JSON → YAML 测试用例

用法：
  # 生成到默认目录 tests/api/cases/
  python generate_api_cases.py data/requests/merchant_1_staging_requests.json

  # 指定输出目录
  python generate_api_cases.py data/requests/merchant_1_staging_requests.json \\
      --output-dir tests/api/cases

  # 给文件名加前缀（区分来源）
  python generate_api_cases.py data/requests/merchant_1_staging_requests.json \\
      --prefix m1_staging
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.case_generator import CaseGenerator
from utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从拦截 JSON 生成 YAML 测试用例（第二层）"
    )
    parser.add_argument("input_file", help="拦截请求 JSON 文件路径")
    parser.add_argument(
        "--output-dir", "-d",
        default="tests/api/cases",
        help="YAML 输出目录（默认: tests/api/cases）",
    )
    parser.add_argument(
        "--prefix", "-p",
        default="",
        help="YAML 文件名前缀，用于区分不同录制批次",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    if not input_path.exists():
        logger.error(f"输入文件不存在: {input_path}")
        sys.exit(1)

    try:
        gen = CaseGenerator(output_dir=args.output_dir)
        files = gen.generate_from_file(str(input_path), prefix=args.prefix)

        if files:
            print(f"\n✅ 生成 {len(files)} 个 YAML case 文件:")
            for f in files:
                print(f"   {f}")
            print(f"\n下一步：python generate_api_tests.py {args.output_dir}")
        else:
            print("⚠️  未生成任何文件（过滤后无有效请求）")

    except Exception as exc:
        logger.error(f"生成失败: {exc}")
        raise


if __name__ == "__main__":
    main()
