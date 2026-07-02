"""
API 测试基类
支持通过 fixture 注入 base_url（多商户），同时保留原有接口兼容性
"""
import time
from typing import Any, Dict, Optional

import requests
from jsonschema import validate, ValidationError
from requests import Response, Session

from utils.logger import get_logger

logger = get_logger(__name__)


class APITestBase:
    """
    HTTP 客户端封装。

    fixture 用法（推荐，base_url 由 merchant_cfg 注入）:
        def test_login(api_client):
            resp = api_client.send_request("POST", "/api/v1/login", json={...})
            api_client.assert_status_code(resp, 200)

    直接实例化（单独脚本 / legacy）:
        client = APITestBase(base_url="https://api.merchant1.example.com")
    """

    def __init__(self, base_url: Optional[str] = None):
        if base_url:
            self._base_url = base_url.rstrip("/")
        else:
            # 向后兼容：从全局 config singleton 读取
            from core.config_manager import config as _cfg
            api_cfg = _cfg.get_api_config()
            self._base_url = (
                _cfg.api_url or api_cfg.get("base_url", "")
            ).rstrip("/")

        api_cfg_timeout = self._load_timeout()
        self.timeout = api_cfg_timeout
        self.session: Session = self._build_session()
        logger.info(f"APITestBase 初始化 | base_url={self._base_url}")

    def _load_timeout(self) -> int:
        try:
            from core.config_manager import config as _cfg
            return _cfg.get("api.timeout", 30)
        except Exception:
            return 30

    def _build_session(self) -> Session:
        s = requests.Session()
        s.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        return s

    # ─── 生命周期（pytest class 模式兼容） ───────────────────────────────────

    def setup_method(self) -> None:
        logger.info("开始 API 测试")

    def teardown_method(self) -> None:
        logger.info("API 测试结束")

    # ─── 核心发送方法 ────────────────────────────────────────────────────────

    def send_request(self, method: str, url: str, **kwargs) -> Response:
        """
        发送 HTTP 请求。url 可以是相对路径或完整 URL。

        自动生成的测试使用相对路径（如 /api/v1/login），
        本方法会自动拼接 base_url。
        """
        if not url.startswith("http"):
            url = self._base_url.rstrip("/") + "/" + url.lstrip("/")

        kwargs.setdefault("timeout", self.timeout)

        logger.info(f"[{method}] {url}")
        if "json" in kwargs:
            logger.debug(f"请求体: {kwargs['json']}")

        start = time.time()
        try:
            resp = self.session.request(method, url, **kwargs)
            elapsed_ms = (time.time() - start) * 1000
            resp.elapsed_ms = elapsed_ms  # type: ignore[attr-defined]
            logger.info(f"响应: {resp.status_code} ({elapsed_ms:.0f}ms)")
            return resp
        except requests.RequestException as exc:
            logger.error(f"请求失败: {exc}")
            raise

    def get(self, url: str, **kwargs) -> Response:
        return self.send_request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> Response:
        return self.send_request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> Response:
        return self.send_request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> Response:
        return self.send_request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> Response:
        return self.send_request("DELETE", url, **kwargs)

    # ─── 断言方法（与原始接口保持一致） ──────────────────────────────────────

    def assert_status_code(self, response: Response, expected_code: int) -> None:
        assert response.status_code == expected_code, (
            f"状态码不匹配: 期望 {expected_code}, 实际 {response.status_code}\n"
            f"响应体: {response.text[:500]}"
        )

    def assert_response_time(self, response: Response, max_time: int) -> None:
        actual = getattr(
            response, "elapsed_ms", response.elapsed.total_seconds() * 1000
        )
        assert actual <= max_time, (
            f"响应超时: 期望 <={max_time}ms, 实际 {actual:.0f}ms"
        )

    def assert_json_schema(self, response: Response, schema: Dict[str, Any]) -> None:
        try:
            validate(instance=response.json(), schema=schema)
        except ValidationError as exc:
            raise AssertionError(f"JSON schema 验证失败: {exc.message}")

    def assert_json_contains(
        self, response: Response, expected_data: Dict[str, Any]
    ) -> None:
        body = response.json()
        for key, expected in expected_data.items():
            assert key in body, f"响应中缺少键: {key}"
            assert body[key] == expected, (
                f"'{key}' 期望 {expected!r}, 实际 {body[key]!r}"
            )

    def assert_header_exists(self, response: Response, header_name: str) -> None:
        assert header_name in response.headers, f"响应头中缺少: {header_name}"

    def assert_header_value(
        self, response: Response, header_name: str, expected_value: str
    ) -> None:
        self.assert_header_exists(response, header_name)
        actual = response.headers[header_name]
        assert actual == expected_value, (
            f"响应头 '{header_name}' 期望 {expected_value!r}, 实际 {actual!r}"
        )

    def assert_contains_text(self, response: Response, text: str) -> None:
        assert text in response.text, f"响应体中不包含文本: {text}"

    # ─── Auth 辅助 ───────────────────────────────────────────────────────────

    def set_auth_token(self, token: str, scheme: str = "Bearer") -> None:
        self.session.headers.update({"Authorization": f"{scheme} {token}"})

    def clear_auth(self) -> None:
        self.session.headers.pop("Authorization", None)

    def login(
        self, username: str, password: str, login_path: str = "/api/v1/login"
    ) -> str:
        resp = self.post(login_path, json={"username": username, "password": password})
        self.assert_status_code(resp, 200)
        token = resp.json().get("token") or resp.json().get("access_token", "")
        if token:
            self.set_auth_token(token)
        return token

    def close(self) -> None:
        self.session.close()
