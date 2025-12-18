#!/usr/bin/env python
"""
智能测试运行器
支持 UI 测试 -> API 变化检测 -> 自动生成 API 测试 -> 运行 API 测试的完整流程
"""
import argparse
import sys
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.api_generator import APITestGenerator
from core.api_change_detector import APIChangeDetector
from utils.logger import get_logger
from utils.helpers import load_json

logger = get_logger(__name__)


class SmartTestRunner:
    """智能测试运行器"""
    
    def __init__(self, headless: bool = False, parallel: int = 0, report: bool = True):
        """
        初始化运行器
        
        Args:
            headless: 是否无头模式
            parallel: 并行进程数(0表示不并行)
            report: 是否生成报告
        """
        self.headless = headless
        self.parallel = parallel
        self.report = report
        self.detector = APIChangeDetector()
        self.generator = APITestGenerator()
        self.ui_report_name = None
        self.api_report_name = None
    
    def run_ui_tests(self) -> bool:
        """
        运行 UI 测试
        
        Returns:
            bool: 是否成功
        """
        logger.info("=" * 60)
        logger.info("步骤 1: 运行 UI 测试")
        logger.info("=" * 60)
        
        cmd = ['pytest', '-v', '-m', 'ui', 'tests/ui/']
        
        if self.parallel > 0:
            cmd.extend(['-n', str(self.parallel)])
        
        if self.report:
            Path('reports/ui').mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_name = f'{timestamp}_UI.html'
            self.ui_report_name = f'reports/ui/{report_name}'
            cmd.extend([f'--html={self.ui_report_name}', '--self-contained-html'])
        
        if self.headless:
            import os
            os.environ['HEADLESS'] = 'true'
        
        logger.info(f"运行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        
        success = result.returncode == 0
        if success:
            logger.info("✅ UI 测试完成")
        else:
            logger.error("❌ UI 测试失败")
        
        return success
    
    def detect_api_changes(self) -> tuple:
        """
        检测 API 变化
        
        Returns:
            tuple: (是否有变化, 新增请求, 变化请求, 最新请求文件)
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤 2: 检测 API 变化")
        logger.info("=" * 60)
        
        # 查找最新的请求文件
        requests_dir = Path('data/requests')
        if not requests_dir.exists():
            logger.warning("没有找到拦截的请求数据")
            return False, [], [], None
        
        request_files = list(requests_dir.glob('requests_*.json'))
        if not request_files:
            logger.warning("没有找到拦截的请求文件")
            return False, [], [], None
        
        # 获取最新的请求文件
        latest_file = max(request_files, key=lambda p: p.stat().st_mtime)
        logger.info(f"📁 最新请求文件: {latest_file.name}")
        
        # 加载请求数据
        data = load_json(latest_file)
        requests = data.get('requests', [])
        logger.info(f"📊 拦截的请求总数: {len(requests)}")
        
        if not requests:
            logger.warning("请求文件中没有数据")
            return False, [], [], latest_file
        
        # 检测变化
        new_requests, changed_requests, has_changes = self.detector.detect_changes(requests)
        
        # 输出摘要
        summary = self.detector.get_summary(new_requests, changed_requests)
        logger.info(f"\n{summary}")
        
        return has_changes, new_requests, changed_requests, latest_file
    
    def regenerate_api_tests(self, requests_file: Path) -> Optional[str]:
        """
        重新生成 API 测试用例
        
        Args:
            requests_file: 请求文件路径
            
        Returns:
            Optional[str]: 生成的测试文件路径
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤 3: 重新生成 API 测试用例")
        logger.info("=" * 60)
        
        try:
            output_file = self.generator.generate_from_file(
                str(requests_file),
                output_file="test_auto_generated.py"
            )
            logger.info(f"✅ 测试用例已生成: {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"❌ 生成测试用例失败: {e}")
            return None
    
    def run_api_tests(self) -> bool:
        """
        运行 API 测试
        
        Returns:
            bool: 是否成功
        """
        logger.info("\n" + "=" * 60)
        logger.info("步骤 4: 运行 API 测试")
        logger.info("=" * 60)
        
        cmd = ['pytest', '-v', '-m', 'api', 'tests/api/']
        
        if self.parallel > 0:
            cmd.extend(['-n', str(self.parallel)])
        
        if self.report:
            Path('reports/api').mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_name = f'{timestamp}_API.html'
            self.api_report_name = f'reports/api/{report_name}'
            cmd.extend([f'--html={self.api_report_name}', '--self-contained-html'])
        
        logger.info(f"运行命令: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        
        success = result.returncode == 0
        if success:
            logger.info("✅ API 测试完成")
        else:
            logger.error("❌ API 测试失败")
        
        return success
    
    def run_full_workflow(self) -> bool:
        """
        运行完整的测试流程
        
        Returns:
            bool: 是否成功
        """
        logger.info("\n" + "🚀" * 30)
        logger.info("开始智能测试流程")
        logger.info("🚀" * 30 + "\n")
        
        # 1. 运行 UI 测试
        ui_success = self.run_ui_tests()
        if not ui_success:
            logger.warning("⚠️  UI 测试失败,但继续执行后续步骤")
        
        # 2. 检测 API 变化
        has_changes, new_reqs, changed_reqs, latest_file = self.detect_api_changes()
        
        # 3. 如果有变化,重新生成测试用例
        if has_changes and latest_file:
            logger.info("\n🔄 检测到 API 变化,重新生成测试用例...")
            self.regenerate_api_tests(latest_file)
        else:
            logger.info("\n✅ 没有 API 变化,跳过测试用例生成")
        
        # 4. 运行 API 测试
        api_success = self.run_api_tests()
        
        # 总结
        logger.info("\n" + "=" * 60)
        logger.info("测试流程完成")
        logger.info("=" * 60)
        logger.info(f"UI 测试: {'✅ 通过' if ui_success else '❌ 失败'}")
        logger.info(f"API 测试: {'✅ 通过' if api_success else '❌ 失败'}")
        
        if has_changes:
            logger.info(f"API 变化: 🆕 {len(new_reqs)} 个新增, 🔄 {len(changed_reqs)} 个变化")
        
        if self.report:
            logger.info("\n📊 测试报告:")
            if self.ui_report_name:
                logger.info(f"  UI: {self.ui_report_name}")
            if self.api_report_name:
                logger.info(f"  API: {self.api_report_name}")
        
        return ui_success and api_success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='智能测试运行器 - UI测试 -> API变化检测 -> 自动生成 -> API测试'
    )
    parser.add_argument(
        'mode',
        choices=['ui', 'api', 'full'],
        help='测试模式: ui(仅UI), api(仅API), full(完整流程)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='无头模式运行浏览器'
    )
    parser.add_argument(
        '-p', '--parallel',
        type=int,
        default=0,
        metavar='N',
        help='并行运行测试(指定进程数)'
    )
    parser.add_argument(
        '--no-report',
        action='store_true',
        help='不生成 HTML 报告'
    )
    parser.add_argument(
        '--clear-cache',
        action='store_true',
        help='清空 API 缓存(强制重新生成所有测试)'
    )
    
    args = parser.parse_args()
    
    # 清空缓存
    if args.clear_cache:
        detector = APIChangeDetector()
        detector.clear_cache()
        logger.info("✅ API 缓存已清空")
        if args.mode == 'full':
            logger.info("将重新生成所有 API 测试用例\n")
    
    # 创建运行器
    runner = SmartTestRunner(
        headless=args.headless,
        parallel=args.parallel,
        report=not args.no_report
    )
    
    # 运行测试
    try:
        if args.mode == 'ui':
            success = runner.run_ui_tests()
        elif args.mode == 'api':
            success = runner.run_api_tests()
        else:  # full
            success = runner.run_full_workflow()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  测试被用户中断")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n❌ 测试运行失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
