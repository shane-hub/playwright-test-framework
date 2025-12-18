"""
UI 测试基类
提供 Playwright UI 测试的基础功能
"""
import pytest
from pathlib import Path
from typing import Optional, Dict, Any
from playwright.sync_api import Page, Browser, BrowserContext, Playwright, sync_playwright

from core.config_manager import config
from core.request_interceptor import RequestInterceptor
from utils.logger import get_logger
from utils.helpers import ensure_dir, get_timestamp

logger = get_logger(__name__)


class UITestBase:
    """UI 测试基类"""
    
    # 类级别的 Playwright 实例
    playwright: Optional[Playwright] = None
    browser: Optional[Browser] = None
    
    # 实例级别的属性
    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    interceptor: Optional[RequestInterceptor] = None
    
    @classmethod
    def setup_class(cls):
        """类级别的设置 - 启动浏览器"""
        logger.info("启动浏览器...")
        
        browser_config = config.get_browser_config()
        browser_type = browser_config.get('type', 'chromium')
        
        cls.playwright = sync_playwright().start()
        
        # 获取浏览器实例
        if browser_type == 'chromium':
            browser_launcher = cls.playwright.chromium
        elif browser_type == 'firefox':
            browser_launcher = cls.playwright.firefox
        elif browser_type == 'webkit':
            browser_launcher = cls.playwright.webkit
        else:
            raise ValueError(f"不支持的浏览器类型: {browser_type}")
        
        # 启动浏览器
        launch_options = {
            'headless': browser_config.get('headless', False),
            'slow_mo': browser_config.get('slow_mo', 0),
        }
        
        if 'args' in browser_config:
            launch_options['args'] = browser_config['args']
        
        cls.browser = browser_launcher.launch(**launch_options)
        logger.info(f"浏览器启动成功: {browser_type}")
    
    @classmethod
    def teardown_class(cls):
        """类级别的清理 - 关闭浏览器"""
        if cls.browser:
            cls.browser.close()
            logger.info("浏览器已关闭")
        
        if cls.playwright:
            cls.playwright.stop()
            logger.info("Playwright 已停止")
    
    def setup_method(self):
        """测试方法级别的设置 - 创建新的上下文和页面"""
        logger.info("创建新的浏览器上下文和页面...")
        
        browser_config = config.get_browser_config()
        
        # 创建上下文
        context_options = {}
        
        if 'viewport' in browser_config:
            context_options['viewport'] = browser_config['viewport']
        
        # 视频录制配置
        video_config = browser_config.get('video', {})
        if video_config.get('enabled', False):
            video_dir = ensure_dir(video_config.get('dir', 'reports/videos'))
            context_options['record_video_dir'] = str(video_dir)
        
        self.context = self.browser.new_context(**context_options)
        self.page = self.context.new_page()
        
        # 设置默认超时
        timeout = browser_config.get('timeout', 30000)
        self.page.set_default_timeout(timeout)
        
        # 启用请求拦截(如果配置启用)
        if config.is_interception_enabled():
            self.enable_interception()
        
        logger.info("页面创建成功")
    
    def teardown_method(self):
        """测试方法级别的清理 - 关闭上下文"""
        # 保存拦截的请求
        if self.interceptor and self.interceptor.get_requests():
            try:
                self.interceptor.save_requests()
                summary = self.interceptor.get_summary()
                logger.info(f"请求拦截摘要: {summary}")
            except Exception as e:
                logger.error(f"保存请求数据失败: {e}")
        
        # 关闭页面和上下文
        if self.page:
            self.page.close()
        
        if self.context:
            self.context.close()
        
        logger.info("浏览器上下文已关闭")
    
    def enable_interception(self) -> RequestInterceptor:
        """
        启用请求拦截
        
        Returns:
            RequestInterceptor: 拦截器实例
        """
        interception_config = config.get_interception_config()
        
        self.interceptor = RequestInterceptor(
            hosts=interception_config.get('hosts', []),
            save_dir=interception_config.get('requests_dir', 'data/requests'),
            deduplicate=interception_config.get('deduplicate', True),
            ignore_resource_types=interception_config.get('ignore_resource_types', [])
        )
        
        # 注意: 同步 API 不支持 route,需要使用异步或者不同的方式
        # 这里我们使用 route 的同步版本
        def handle_route(route):
            """同步路由处理器包装"""
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.interceptor._handle_route(route))
            finally:
                loop.close()
        
        self.page.route("**/*", handle_route)
        logger.info("请求拦截已启用")
        
        return self.interceptor
    
    def take_screenshot(self, name: Optional[str] = None, full_page: bool = False) -> str:
        """
        截图
        
        Args:
            name: 截图文件名,不指定则使用时间戳
            full_page: 是否截取整个页面
            
        Returns:
            str: 截图文件路径
        """
        screenshot_config = config.get('browser.screenshot', {})
        screenshot_dir = ensure_dir(screenshot_config.get('dir', 'reports/screenshots'))
        
        if not name:
            name = f"screenshot_{get_timestamp()}.png"
        elif not name.endswith('.png'):
            name = f"{name}.png"
        
        filepath = screenshot_dir / name
        self.page.screenshot(path=str(filepath), full_page=full_page)
        
        logger.info(f"截图已保存: {filepath}")
        return str(filepath)
    
    def navigate(self, url: str, wait_until: str = "load") -> None:
        """
        导航到指定 URL
        
        Args:
            url: 目标 URL
            wait_until: 等待条件 ('load', 'domcontentloaded', 'networkidle')
        """
        logger.info(f"导航到: {url}")
        self.page.goto(url, wait_until=wait_until)
    
    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> None:
        """
        等待元素出现
        
        Args:
            selector: CSS 选择器
            timeout: 超时时间(毫秒)
        """
        self.page.wait_for_selector(selector, timeout=timeout)
    
    def click(self, selector: str) -> None:
        """
        点击元素
        
        Args:
            selector: CSS 选择器
        """
        logger.debug(f"点击元素: {selector}")
        self.page.click(selector)
    
    def fill(self, selector: str, value: str) -> None:
        """
        填充输入框
        
        Args:
            selector: CSS 选择器
            value: 填充值
        """
        logger.debug(f"填充 {selector}: {value}")
        self.page.fill(selector, value)
    
    def get_text(self, selector: str) -> str:
        """
        获取元素文本
        
        Args:
            selector: CSS 选择器
            
        Returns:
            str: 元素文本
        """
        return self.page.text_content(selector)
