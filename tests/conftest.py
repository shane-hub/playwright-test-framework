"""
pytest fixtures 配置
"""
import pytest
from base.api_test_base import APITestBase


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
