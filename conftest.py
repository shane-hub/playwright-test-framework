"""
全局 conftest.py
多商户 × 多环境 fixture 体系 + 功能自动跳过 + 请求拦截 + 可选自动生成
"""
import asyncio
import os
import re
from typing import Generator, List, Optional

import pytest
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

from core.config_manager import ConfigManager
from core.request_interceptor import RequestInterceptor
from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)

# pytest-xdist worker 标识，用于文件名去重
_WORKER_ID = os.environ.get("PYTEST_XDIST_WORKER", "master")


# ─── CLI 选项 ──────────────────────────────────────────────────────────────────

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--merchant", default="merchant_1",
        help="目标商户，例如: --merchant=merchant_2",
    )
    parser.addoption(
        "--env", default="dev",
        choices=["dev", "staging", "prod"],
        help="测试环境，例如: --env=staging",
    )
    parser.addoption(
        "--generate-cases", action="store_true", default=False,
        help="UI 测试完成后自动生成 YAML case 文件（第二层）",
    )
    parser.addoption(
        "--generate-tests", action="store_true", default=False,
        help="UI 测试完成后自动生成 pytest 脚本（第二层+第三层）",
    )


# ─── 核心 Fixture ──────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def merchant_cfg(request: pytest.FixtureRequest) -> ConfigManager:
    """会话级商户配置，所有 fixture 和用例共享同一实例"""
    merchant = request.config.getoption("--merchant")
    env      = request.config.getoption("--env")
    cfg = ConfigManager(merchant=merchant, env=env)
    logger.info(f"测试会话启动 | 商户={merchant} | 环境={env} | worker={_WORKER_ID}")
    return cfg


# ─── 功能自动跳过 ──────────────────────────────────────────────────────────────

def pytest_runtest_setup(item: pytest.Item) -> None:
    """@pytest.mark.requires_feature → 商户不支持时自动 skip"""
    merchant = item.config.getoption("--merchant", default="merchant_1")
    env      = item.config.getoption("--env",      default="dev")
    cfg = ConfigManager(merchant=merchant, env=env)  # 单例，直接返回

    for mark in item.iter_markers("requires_feature"):
        feature = mark.args[0]
        if not cfg.has_feature(feature):
            pytest.skip(f"[{merchant}] 不支持功能: {feature}")


# ─── Session Token（整个 session 只登录一次）─────────────────────────────────

@pytest.fixture(scope="session")
def _session_token(merchant_cfg: ConfigManager) -> str:
    """
    会话级 token。登录一次，token 存在内存中，所有用例复用。
    pytest-xdist 下每个 worker 各自登录一次（总登录次数 = worker 数，不是用例数）。
    """
    creds = merchant_cfg.get("credentials", {})
    if not creds.get("username"):
        logger.info("未配置 credentials，跳过自动登录")
        return ""

    from base.api_test_base import APITestBase
    tmp = APITestBase(base_url=merchant_cfg.api_url)
    try:
        token = tmp.login(
            username=creds["username"],
            password=creds["password"],
            login_path=creds.get("login_path", "/api/v1/login"),
        )
        logger.info(f"[{_WORKER_ID}] 登录成功，token 已缓存")
        return token
    except Exception as exc:
        logger.error(f"[{_WORKER_ID}] 登录失败: {exc} —— 需要 token 的用例将收到 401")
        return ""
    finally:
        tmp.close()


# ─── API Fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="function")
def api_client(merchant_cfg: ConfigManager, _session_token: str):
    """
    函数级 API 客户端（每条用例独立 session，避免状态污染）。
    token 从 _session_token 注入（不重新登录），通过 client._cached_token 供用例使用。

    用法：
        def test_orders(api_client, case):
            if case.get("need_token"):
                api_client.set_auth_token(api_client._cached_token)
            resp = api_client.send_request(...)
    """
    from base.api_test_base import APITestBase
    client = APITestBase(base_url=merchant_cfg.api_url)
    client._cached_token = _session_token   # 缓存 token，不注入，由用例按需设置
    yield client
    client.close()


# ─── 拦截请求收集器（会话级，跨用例积累）─────────────────────────────────────

@pytest.fixture(scope="session")
def _request_collector() -> List[dict]:
    return []


# ─── UI Fixture ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def browser(merchant_cfg: ConfigManager):
    """会话级浏览器（同一 worker 内所有 UI 用例共享）"""
    browser_cfg  = merchant_cfg.get_browser_config()
    browser_type = browser_cfg.get("type", "chromium")

    with sync_playwright() as pw:
        b: Browser = getattr(pw, browser_type).launch(
            headless=browser_cfg.get("headless", False),
            slow_mo=browser_cfg.get("slow_mo", 0),
            args=browser_cfg.get("args", []),
        )
        logger.info(f"浏览器启动 | {browser_type} | worker={_WORKER_ID}")
        yield b
        b.close()


@pytest.fixture(scope="function")
def context(browser: Browser, merchant_cfg: ConfigManager) -> BrowserContext:
    """函数级浏览器上下文（每条用例隔离）"""
    browser_cfg  = merchant_cfg.get_browser_config()
    ctx_options: dict = {}

    if "viewport" in browser_cfg:
        ctx_options["viewport"] = browser_cfg["viewport"]

    video_cfg = browser_cfg.get("video", {})
    if video_cfg.get("enabled", False):
        ctx_options["record_video_dir"] = str(
            ensure_dir(video_cfg.get("dir", "reports/videos"))
        )

    ctx: BrowserContext = browser.new_context(**ctx_options)
    yield ctx
    ctx.close()


@pytest.fixture(scope="function")
def page(
    context: BrowserContext,
    merchant_cfg: ConfigManager,
    _request_collector: List[dict],
) -> Page:
    """
    函数级 Page，自动导航到 web_url，按商户 hosts 启用拦截。
    每条用例拦截到的请求追加进 session 级收集器，session 结束时统一保存。
    """
    pg: Page = context.new_page()
    pg.set_default_timeout(merchant_cfg.get("browser.timeout", 30000))

    # 启用拦截
    interceptor: Optional[RequestInterceptor] = None
    if merchant_cfg.is_interception_enabled():
        ic = merchant_cfg.get_interception_config()
        hosts = merchant_cfg.get_intercept_hosts()
        interceptor = RequestInterceptor(
            hosts=hosts,
            save_dir=ic.get("requests_dir", "data/requests"),
            deduplicate=ic.get("deduplicate", True),
            ignore_resource_types=ic.get("ignore_resource_types", []),
        )

        def _sync_handler(route):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(interceptor._handle_route(route))
            finally:
                loop.close()

        pg.route("**/*", _sync_handler)
        logger.info(f"[{merchant_cfg.merchant}] 拦截已启用 | hosts={hosts}")

    if merchant_cfg.web_url:
        pg.goto(merchant_cfg.web_url, wait_until="networkidle")

    yield pg

    # 追加本次拦截结果
    if interceptor:
        captured = interceptor.get_requests()
        if captured:
            _request_collector.extend(captured)

    if not pg.is_closed():
        report_cfg    = merchant_cfg.get_report_config("ui")
        screenshot_dir = ensure_dir(report_cfg.get("output_dir", "reports/ui"))
        safe_title    = re.sub(r'[\\/:*?"<>|]', "_", pg.title()[:30])
        pg.screenshot(
            path=str(screenshot_dir / f"teardown_{safe_title}_{_WORKER_ID}.png")
        )
        pg.close()


# ─── Session 结束：保存请求 + 可选自动生成 ────────────────────────────────────

@pytest.fixture(scope="session", autouse=True)
def _auto_generate(
    request: pytest.FixtureRequest,
    merchant_cfg: ConfigManager,
    _request_collector: List[dict],
) -> Generator[None, None, None]:
    """
    Session 结束时：
    1. 保存拦截请求到 JSON
    2. --generate-cases  → 自动生成 YAML case 文件
    3. --generate-tests  → 自动生成 YAML + pytest 脚本
    """
    yield  # 等所有用例跑完

    if not _request_collector:
        return

    # 保存 JSON
    from core.request_interceptor import RequestInterceptor
    ic = merchant_cfg.get_interception_config()
    tmp = RequestInterceptor(
        hosts=[],
        save_dir=ic.get("requests_dir", "data/requests"),
    )
    tmp.intercepted_requests = _request_collector
    json_path = tmp.save_requests(
        filename=f"{merchant_cfg.merchant}_{merchant_cfg.env}_{_WORKER_ID}_requests.json"
    )
    logger.info(f"已保存 {len(_request_collector)} 条请求 → {json_path}")

    do_cases = request.config.getoption("--generate-cases", default=False)
    do_tests = request.config.getoption("--generate-tests", default=False)

    if do_cases or do_tests:
        if _WORKER_ID != "master":
            # xdist 各 worker 并发写同一批文件会产生冲突，跳过自动生成
            # 录制完成后手动运行: python generate_api_cases.py data/requests/<file>.json
            logger.warning(
                f"[{_WORKER_ID}] xdist 模式下跳过自动生成（并发写冲突风险）"
                " —— 请手动执行 generate_api_cases.py / generate_api_tests.py"
            )
        else:
            from core.case_generator import CaseGenerator
            cases_dir = "tests/api/cases"
            gen = CaseGenerator(output_dir=cases_dir)
            yaml_files = gen.generate_from_requests(_request_collector)
            logger.info(f"已生成 {len(yaml_files)} 个 YAML case 文件 → {cases_dir}")

            if do_tests:
                from core.api_generator import APITestGenerator
                tests_dir = "tests/api/generated"
                gen2 = APITestGenerator(output_dir=tests_dir)
                py_files = gen2.generate_from_yaml_dir(cases_dir)
                logger.info(f"已生成 {len(py_files)} 个 pytest 脚本 → {tests_dir}")


# ─── 注册自定义 Mark ────────────────────────────────────────────────────────────

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "requires_feature(feature): 当前商户不支持该功能时自动 skip",
    )
