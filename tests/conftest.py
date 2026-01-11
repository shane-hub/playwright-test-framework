"""
pytest fixtures 配置
"""
import pytest
from base.api_test_base import APITestBase
from core.config_manager import config as app_config
from utils.logger import get_logger

logger = get_logger(__name__)


def pytest_addoption(parser):
    """添加命令行参数"""
    parser.addoption(
        "--merchant", 
        action="store", 
        default=None, 
        help="指定运行的商户 (e.g. merchant_a)"
    )
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="指定运行环境 (test, prod 等)，如果不指定则使用 config.yaml 中的 environment 配置"
    )


def pytest_configure(config):
    """
    配置加载时的钩子，用于根据 --merchant 和 --env 参数修改全局配置
    """
    merchant_name = config.getoption("--merchant")
    cli_env = config.getoption("--env")
    
    # 确定最终环境: 命令行参数 > 配置文件
    if cli_env:
        target_env = cli_env
        app_config._config["environment"] = target_env
        logger.info(f"使用命令行指定的环境: {target_env}")
    else:
        target_env = app_config.get("environment", "test")
        logger.info(f"使用配置文件/默认环境: {target_env}")

    if merchant_name:
        logger.info(f"收到商户参数: {merchant_name}")
        # 获取 merchants 配置
        merchants_config = app_config.get("merchants")
        
        if not merchants_config:
             pytest.exit(f"错误: 配置文件中未找到 'merchants' 部分")

        if merchant_name not in merchants_config:
            pytest.exit(f"错误: 未找到商户配置 '{merchant_name}'，可用商户: {list(merchants_config.keys())}")
        
        # 获取特定商户的配置
        merchant_root_config = merchants_config[merchant_name]
        
        # 尝试获取特定环境的配置
        if target_env in merchant_root_config:
             target_merchant_config = merchant_root_config[target_env]
             logger.info(f"已加载商户 '{merchant_name}' 的 '{target_env}' 环境配置")
        else:
             # 如果没有找到特定环境配置，回退到根配置 (兼容旧结构或通用配置)
             logger.warning(f"未找到商户 '{merchant_name}' 的 '{target_env}' 环境配置，尝试使用通用配置")
             target_merchant_config = merchant_root_config
        
        # 覆盖 API URL
        if "api_url" in target_merchant_config:
            # 确保 api 配置存在
            if "api" not in app_config._config:
                app_config._config["api"] = {}
            
            old_url = app_config._config["api"].get("base_url")
            app_config._config["api"]["base_url"] = target_merchant_config["api_url"]
            logger.info(f"已将 API base_url 从 '{old_url}' 更新为: '{target_merchant_config['api_url']}'")
            
        # 覆盖 UI URL (如果需要)
        if "ui_url" in target_merchant_config:
             if "ui" not in app_config._config:
                app_config._config["ui"] = {}
             # 假设 UI base_url 存在 ui.base_url 中，或者需要根据实际情况调整
             app_config._config["ui"]["base_url"] = target_merchant_config["ui_url"]
             
        # 覆盖拦截 Hosts
        if "interception_hosts" in target_merchant_config:
            if "interception" not in app_config._config:
                app_config._config["interception"] = {}
            
            old_hosts = app_config._config["interception"].get("hosts", [])
            app_config._config["interception"]["hosts"] = target_merchant_config["interception_hosts"]
            logger.info(f"已将拦截 hosts 从 {old_hosts} 更新为: {target_merchant_config['interception_hosts']}")

        # 将当前商户信息存入 config，以便后续 fixture 使用
        app_config._config["current_merchant"] = target_merchant_config
        app_config._config["current_merchant_name"] = merchant_name


def pytest_collection_modifyitems(config, items):
    """
    根据 @pytest.mark.merchant 过滤测试用例
    """
    selected_merchant = config.getoption("--merchant")
    
    skip_msg = f"Skipped: test not for selected merchant '{selected_merchant}'"
    skip_merchant = pytest.mark.skip(reason=skip_msg)
    skip_no_merchant = pytest.mark.skip(reason="Skipped: --merchant not specified")
    
    for item in items:
        # 获取 merchant 标记
        merchant_marker = item.get_closest_marker("merchant")
        
        if merchant_marker:
            # 如果测试用例标记了特定商户
            allowed_merchants = merchant_marker.args
            
            if selected_merchant:
                # 如果指定了商户，且不在允许列表中，则跳过
                if selected_merchant not in allowed_merchants:
                    item.add_marker(skip_merchant)
            else:
                # 如果没指定商户，跳过那些必须指定商户才能跑的用例
                item.add_marker(skip_no_merchant)
        else:
            # 没有标记的用例，被视为"通用"用例
            # 可以在所有商户下运行，也可以在不指定商户时运行(使用默认配置)
            pass


@pytest.fixture(scope="function")
def api_client():
    """
    API 客户端 fixture
    
    Returns:
        APITestBase: API 测试客户端实例
    """
    client = APITestBase()
    client.setup_method()
    
    yield client
    
    client.teardown_method()


@pytest.fixture(scope="session")
def test_config():
    """
    测试配置 fixture
    
    Returns:
        dict: 测试配置
    """
    from core.config_manager import config
    return config
