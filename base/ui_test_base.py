"""
UI 测试基类
保留原有 setup_class/setup_method 生命周期以兼容存量用例，
enable_interception 接受可选 merchant_cfg 参数，
使每个商户只拦截自己域名下的请求。
"""
import asyncio
from typing import Optional, Dict, Any

from playwright.sync_api import (
    Page, Browser, BrowserContext, Playwright,
    sync_playwright,
)

from core.config_manager import ConfigManager
from core.request_interceptor import RequestInterceptor
from utils.logger import get_logger
from utils.helpers import ensure_dir, get_timestamp

logger = get_logger(__name__)


class UITestBase:
    """
    UI 测试基类（保留 setup_class / setup_method 模式兼容老用例）。

    新用例推荐直接使用 conftest.py 提供的 page / api_client fixture，
    不需要继承本类。
    """

    playwright: Optional[Playwright] = None
    browser: Optional[Browser] = None

    context: Optional[BrowserContext] = None
    page: Optional[Page] = None
    interceptor: Optional[RequestInterceptor] = None

    # ─── 类级别生命周期 ───────────────────────────────────────────────────────

    @classmethod
    def setup_class(cls):
        from core.config_manager import config
        browser_cfg = config.get_browser_config()
        browser_type = browser_cfg.get("type", "chromium")

        cls.playwright = sync_playwright().start()
        launcher = getattr(cls.playwright, browser_type)
        launch_options: Dict[str, Any] = {
            "headless": browser_cfg.get("headless", False),
            "slow_mo":  browser_cfg.get("slow_mo", 0),
        }
        if "args" in browser_cfg:
            launch_options["args"] = browser_cfg["args"]

        cls.browser = launcher.launch(**launch_options)
        logger.info(f"浏览器启动: {browser_type}")

    @classmethod
    def teardown_class(cls):
        if cls.browser:
            cls.browser.close()
            logger.info("浏览器已关闭")
        if cls.playwright:
            cls.playwright.stop()

    # ─── 方法级别生命周期 ────────────────────────────────────────────────────

    def setup_method(self):
        """
        pytest 调用签名：setup_method(self) 或 setup_method(self, method)。
        这里只接受 self，merchant_cfg 通过 setup_with_merchant() 单独传入。
        """
        from core.config_manager import config as _global
        self._do_setup(_global)

    def setup_with_merchant(self, merchant_cfg: ConfigManager) -> None:
        """
        多商户模式下调用，替代直接在 setup_method 里硬读全局 config。

        用法（在子类 setup_method 里调用）：
            def setup_method(self):
                # merchant_cfg 从 pytest fixture 或参数传入
                self.setup_with_merchant(ConfigManager("merchant_2", "staging"))
        """
        self._do_setup(merchant_cfg)

    def _do_setup(self, cfg: ConfigManager) -> None:
        if not self.browser:
            raise RuntimeError(
                "UITestBase.setup_class() 必须在 setup_method() 之前执行，"
                "请确认测试类继承了 UITestBase 且 setup_class 没有提前失败。"
            )
        browser_cfg = cfg.get_browser_config()

        ctx_options: Dict[str, Any] = {}
        if "viewport" in browser_cfg:
            ctx_options["viewport"] = browser_cfg["viewport"]

        video_cfg = browser_cfg.get("video", {})
        if video_cfg.get("enabled", False):
            video_dir = ensure_dir(video_cfg.get("dir", "reports/videos"))
            ctx_options["record_video_dir"] = str(video_dir)

        self.context = self.browser.new_context(**ctx_options)
        self.page = self.context.new_page()
        self.page.set_default_timeout(browser_cfg.get("timeout", 30000))

        if cfg.is_interception_enabled():
            self.enable_interception(merchant_cfg=cfg)

        logger.info("页面创建成功")

    def teardown_method(self):
        if self.interceptor and self.interceptor.get_requests():
            try:
                self.interceptor.save_requests()
                logger.info(f"拦截摘要: {self.interceptor.get_summary()}")
            except Exception as exc:
                logger.error(f"保存请求数据失败: {exc}")

        if self.page:
            self.page.close()
        if self.context:
            self.context.close()

    # ─── 请求拦截 ────────────────────────────────────────────────────────────

    def enable_interception(
        self,
        merchant_cfg: Optional[ConfigManager] = None,
    ) -> RequestInterceptor:
        """
        启用请求拦截。

        merchant_cfg: 提供当前商户的拦截 hosts；
                      不传则使用全局 config（向后兼容）。
        """
        from core.config_manager import config as _global
        cfg: ConfigManager = merchant_cfg or _global

        interception_cfg = cfg.get_interception_config()
        hosts = cfg.get_intercept_hosts()

        self.interceptor = RequestInterceptor(
            hosts=hosts,
            save_dir=interception_cfg.get("requests_dir", "data/requests"),
            deduplicate=interception_cfg.get("deduplicate", True),
            ignore_resource_types=interception_cfg.get("ignore_resource_types", []),
        )

        def _sync_route_handler(route):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.interceptor._handle_route(route))
            finally:
                loop.close()

        self.page.route("**/*", _sync_route_handler)
        logger.info(f"请求拦截已启用 | hosts={hosts}")
        return self.interceptor

    # ─── 页面操作辅助 ────────────────────────────────────────────────────────

    def navigate(self, url: str, wait_until: str = "load") -> None:
        logger.info(f"导航到: {url}")
        self.page.goto(url, wait_until=wait_until)

    def wait_for_selector(self, selector: str, timeout: Optional[int] = None) -> None:
        self.page.wait_for_selector(selector, timeout=timeout)

    def click(self, selector: str) -> None:
        logger.debug(f"点击: {selector}")
        self.page.click(selector)

    def fill(self, selector: str, value: str) -> None:
        logger.debug(f"填充 {selector}: {value}")
        self.page.fill(selector, value)

    def get_text(self, selector: str) -> str:
        return self.page.text_content(selector)

    def take_screenshot(
        self, name: Optional[str] = None, full_page: bool = False
    ) -> str:
        from core.config_manager import config
        screenshot_cfg = config.get("browser.screenshot", {})
        screenshot_dir = ensure_dir(screenshot_cfg.get("dir", "reports/screenshots"))

        if not name:
            name = f"screenshot_{get_timestamp()}.png"
        elif not name.endswith(".png"):
            name += ".png"

        filepath = screenshot_dir / name
        self.page.screenshot(path=str(filepath), full_page=full_page)
        logger.info(f"截图已保存: {filepath}")
        return str(filepath)
