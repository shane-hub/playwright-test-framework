"""
API Case 生成器（第二层）
从拦截的 JSON 请求生成 YAML 测试用例

生成规则：
  正常用例（1条）：录制的原始请求 + 响应状态码
  异常用例（自动推导）：
    - 有 Authorization header → 生成"未携带 Token"用例 → expect 401
    - POST/PUT/PATCH 有 body → 每个顶层字段生成"缺少该字段"用例 → expect 400
    - 路径含动态 ID → 生成"资源不存在"用例（替换为不存在的 ID）→ expect 404
  边界用例（字段级别）：
    - string 字段 → 空字符串 → expect 400
    - string 字段 → 256字符超长 → expect 400
    - number 字段 → 负数 → expect 400

need_token：从拦截 headers 自动判断（有 Authorization → true）
feature：根据路径前缀自动映射（可自定义 feature_map）
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import yaml

from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)

# 过滤掉敏感或自动头
_SKIP_HEADERS = {
    "host", "content-length", "connection",
    "authorization", "cookie",
}

# 路径 → 功能标记（前缀匹配）
_DEFAULT_FEATURE_MAP: Dict[str, str] = {
    "/api/v1/kyc/level3":  "kyc_level_3",
    "/api/v1/crypto":      "crypto_payment",
    "/api/v1/points":      "points_system",
    "/api/v1/live":        "live_betting",
    "/api/v1/currency":    "multi_currency",
}

# 路径去重 + 归一化（同 api_generator）
_ID_PATTERN = re.compile(
    r"/(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
    r"(?=/|$)",
    re.IGNORECASE,
)

# 只需要生成用例的 HTTP 方法
_METHODS_WITH_BODY = {"POST", "PUT", "PATCH"}

# 字段名 → Faker provider（小写精确匹配 + 包含匹配）
_FAKER_FIELD_MAP: Dict[str, str] = {
    "name":          "name",
    "real_name":     "name",
    "full_name":     "name",
    "fullname":      "name",
    "first_name":    "first_name",
    "last_name":     "last_name",
    "nickname":      "user_name",
    "username":      "user_name",
    "email":         "email",
    "phone":         "phone_number",
    "mobile":        "phone_number",
    "tel":           "phone_number",
    "phone_number":  "phone_number",
    "bank_card":     "credit_card_number",
    "bankcard":      "credit_card_number",
    "card_number":   "credit_card_number",
    "card_no":       "credit_card_number",
    "id_card":       "ssn",
    "id_no":         "ssn",
    "id_number":     "ssn",
    "address":       "address",
    "city":          "city",
    "province":      "province",
    "password":      "password",
    "passwd":        "password",
    "company":       "company",
    "remark":        "sentence",
    "description":   "sentence",
    "desc":          "sentence",
}


class CaseGenerator:

    def __init__(
        self,
        output_dir: str = "tests/api/cases",
        feature_map: Optional[Dict[str, str]] = None,
        skip_paths: Optional[List[str]] = None,
    ):
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)
        self.feature_map = feature_map or _DEFAULT_FEATURE_MAP
        self.skip_paths = skip_paths or [
            "/health", "/ping", "/metrics", "/favicon",
            "/actuator", "/__", "/static/", "/assets/",
        ]

    # ─── 辅助 ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _relative_path(url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path

    @staticmethod
    def _normalize_path(path: str) -> str:
        return _ID_PATTERN.sub("/{id}", path)

    def _dedup_key(self, req: Dict) -> str:
        method = req.get("method", "GET")
        path = urlparse(req.get("url", "")).path
        return f"{method}:{self._normalize_path(path)}"

    def _get_feature(self, path: str) -> Optional[str]:
        for prefix, feature in self.feature_map.items():
            if path.startswith(prefix):
                return feature
        return None

    @staticmethod
    def _detect_faker_fields(body: Dict) -> Dict[str, str]:
        """根据字段名自动识别哪些字段应该用 Faker 动态生成。"""
        result: Dict[str, str] = {}
        for field in body:
            key = field.lower()
            # 精确匹配优先
            if key in _FAKER_FIELD_MAP:
                result[field] = _FAKER_FIELD_MAP[key]
                continue
            # 词边界模糊匹配（user_phone → phone, company_name → company 而非 name）
            # 取最长匹配项，避免 "name" 匹配 "filename" 或 "company_name"
            best_provider: Optional[str] = None
            best_len = 0
            for pattern, provider in _FAKER_FIELD_MAP.items():
                if re.search(r"(?:^|_)" + re.escape(pattern) + r"(?:_|$)", key):
                    if len(pattern) > best_len:
                        best_provider = provider
                        best_len = len(pattern)
            if best_provider:
                result[field] = best_provider
        return result

    def _should_skip(self, req: Dict) -> bool:
        rt = req.get("resource_type", "").lower()
        if rt and rt not in {"xhr", "fetch", "other"}:
            return True
        status = req.get("response", {}).get("status", 0)
        if status >= 500:
            return True
        path = urlparse(req.get("url", "")).path
        if any(path.startswith(p) for p in self.skip_paths):
            return True
        return False

    @staticmethod
    def _yaml_filename(method: str, path: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]", "_", path.strip("/"))
        slug = re.sub(r"_+", "_", slug).strip("_").lower()
        return f"{method.lower()}_{slug}.yaml"

    # ─── Case 生成核心 ────────────────────────────────────────────────────────

    def _build_cases(self, req: Dict) -> List[Dict]:
        method  = req["method"]
        url     = req["url"]
        path    = urlparse(url).path
        headers = req.get("headers", {})
        body    = req.get("body")
        resp    = req.get("response", {})
        status  = resp.get("status", 200)

        need_token  = "authorization" in {k.lower() for k in headers}
        has_body    = isinstance(body, dict) and bool(body)
        has_dyn_id  = bool(_ID_PATTERN.search(path))

        cases: List[Dict] = []
        tc = 1

        # ── 正常用例 ────────────────────────────────────────────────────────
        normal_request: Dict[str, Any] = {"body": body}
        if has_body:
            faker_fields = self._detect_faker_fields(body)
            if faker_fields:
                normal_request["faker_fields"] = faker_fields

        normal: Dict[str, Any] = {
            "id":       f"TC_{tc:03d}",
            "name":     "正常请求",
            "type":     "normal",
            "priority": "P0",
            "request":  normal_request,
            "expect": {
                "status":          status,
                "response_time_ms": 3000,
            },
        }
        if isinstance(resp.get("body"), dict):
            normal["expect"]["json_not_null"] = True
        cases.append(normal)
        tc += 1

        # ── 异常用例 ────────────────────────────────────────────────────────

        # 1. 未携带 Token
        if need_token:
            cases.append({
                "id":         f"TC_{tc:03d}",
                "name":       "[异常] 未携带 Token",
                "type":       "abnormal",
                "priority":   "P0",
                "need_token": False,
                "request":    {"body": body},
                "expect":     {"status": 401},
            })
            tc += 1

        # 2. 缺少必填字段（POST/PUT/PATCH）
        if has_body and method in _METHODS_WITH_BODY:
            for field in list(body.keys())[:5]:   # 最多 5 个字段，避免用例爆炸
                truncated = {k: v for k, v in body.items() if k != field}
                cases.append({
                    "id":       f"TC_{tc:03d}",
                    "name":     f"[异常] 缺少字段 {field}",
                    "type":     "abnormal",
                    "priority": "P1",
                    "request":  {"body": truncated},
                    "expect":   {"status": 400},
                })
                tc += 1

        # 3. 资源不存在（路径含动态 ID）
        if has_dyn_id:
            not_found_path = re.sub(r"/\d+", "/999999999", path)
            not_found_path = re.sub(
                r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
                "/00000000-0000-0000-0000-000000000000",
                not_found_path, flags=re.I,
            )
            cases.append({
                "id":       f"TC_{tc:03d}",
                "name":     "[异常] 资源不存在",
                "type":     "abnormal",
                "priority": "P1",
                "request":  {"path": not_found_path, "body": body},
                "expect":   {"status": 404},
            })
            tc += 1

        # ── 边界用例 ────────────────────────────────────────────────────────
        if has_body:
            for field, value in list(body.items())[:5]:
                if isinstance(value, str):
                    # 空字符串
                    cases.append({
                        "id":       f"TC_{tc:03d}",
                        "name":     f"[边界] {field} 为空字符串",
                        "type":     "boundary",
                        "priority": "P2",
                        "request":  {"body": {**body, field: ""}},
                        "expect":   {"status": 400},
                    })
                    tc += 1
                    # 超长
                    cases.append({
                        "id":       f"TC_{tc:03d}",
                        "name":     f"[边界] {field} 超长（256字符）",
                        "type":     "boundary",
                        "priority": "P2",
                        "request":  {"body": {**body, field: "a" * 256}},
                        "expect":   {"status": 400},
                    })
                    tc += 1

                elif isinstance(value, (int, float)):
                    # 负数
                    cases.append({
                        "id":       f"TC_{tc:03d}",
                        "name":     f"[边界] {field} 为负数",
                        "type":     "boundary",
                        "priority": "P2",
                        "request":  {"body": {**body, field: -1}},
                        "expect":   {"status": 400},
                    })
                    tc += 1

        return cases

    def _build_yaml_doc(self, req: Dict) -> Dict:
        url     = req["url"]
        path    = urlparse(url).path
        headers = req.get("headers", {})

        clean_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in _SKIP_HEADERS
        }
        need_token = "authorization" in {k.lower() for k in headers}
        feature    = self._get_feature(path)

        return {
            "endpoint": {
                "method":     req["method"],
                "path":       self._relative_path(url),
                "need_token": need_token,
                "feature":    feature,
            },
            "headers": clean_headers or None,
            "cases":   self._build_cases(req),
        }

    # ─── 过滤 + 去重 ──────────────────────────────────────────────────────────

    def filter_and_dedup(self, requests: List[Dict]) -> List[Dict]:
        valid = [r for r in requests if not self._should_skip(r)]
        seen: Dict[str, Dict] = {}
        for req in valid:
            key = self._dedup_key(req)
            if key not in seen:
                seen[key] = req
            else:
                # 已有记录时，优先保留 2xx 状态
                existing_status = seen[key].get("response", {}).get("status", 0)
                new_status      = req.get("response", {}).get("status", 0)
                if 200 <= new_status < 300 and not (200 <= existing_status < 300):
                    seen[key] = req
        result = list(seen.values())
        logger.info(f"过滤去重: {len(requests)} → {len(valid)} → {len(result)} 条")
        return result

    # ─── 公开接口 ─────────────────────────────────────────────────────────────

    def generate_from_requests(
        self,
        requests: List[Dict],
        prefix: str = "",
    ) -> List[str]:
        """
        从请求列表生成 YAML case 文件。
        返回生成的文件路径列表。
        """
        filtered = self.filter_and_dedup(requests)
        if not filtered:
            logger.warning("无有效请求可生成")
            return []

        written: List[str] = []
        for req in filtered:
            doc = self._build_yaml_doc(req)
            method = doc["endpoint"]["method"]
            path   = self._normalize_path(urlparse(req["url"]).path)
            fname  = (f"{prefix}_" if prefix else "") + self._yaml_filename(method, path)
            out    = self.output_dir / fname

            with open(out, "w", encoding="utf-8") as f:
                yaml.dump(
                    doc,
                    f,
                    allow_unicode=True,
                    sort_keys=False,
                    default_flow_style=False,
                )
            logger.info(f"已生成: {out} ({len(doc['cases'])} 条用例)")
            written.append(str(out))

        return written

    def generate_from_file(self, json_file: str, prefix: str = "") -> List[str]:
        from utils.helpers import load_json
        data = load_json(json_file)
        return self.generate_from_requests(data.get("requests", []), prefix=prefix)
