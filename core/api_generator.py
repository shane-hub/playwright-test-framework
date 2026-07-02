"""
API 测试脚本生成器（第三层）
从 YAML case 文件生成 pytest 脚本

生成的脚本特点：
  - 参数化：一个端点一个函数，YAML 中每条 case 是一组参数
  - need_token：从 case 读取，决定是否注入 session token（不重新登录）
  - requires_feature：endpoint.feature 不为 null 时自动加 mark
  - path_override：case.request.path 存在时覆盖 endpoint.path（用于"资源不存在"类用例）
  - 测试 ID 用 case.id 字段，pytest -v 输出可读
"""
import re
from pathlib import Path
from typing import List, Optional, Union

import yaml

from utils.helpers import ensure_dir
from utils.logger import get_logger

logger = get_logger(__name__)


class APITestGenerator:

    def __init__(self, output_dir: str = "tests/api/generated"):
        self.output_dir = Path(output_dir)
        ensure_dir(self.output_dir)
        logger.info(f"API 测试生成器初始化 | 输出目录: {output_dir}")

    # ─── 命名辅助 ─────────────────────────────────────────────────────────────

    @staticmethod
    def _sanitize(name: str) -> str:
        s = re.sub(r"[^a-zA-Z0-9_]", "_", name)
        s = re.sub(r"_+", "_", s).strip("_").lower()
        return s or "api"

    def _func_name(self, method: str, path: str) -> str:
        parts = [p for p in path.split("/") if p and not re.match(r"^\d+$|^\{id\}$", p)]
        suffix = "_".join(self._sanitize(p) for p in parts[-3:]) or "root"
        return f"test_{method.lower()}_{suffix}"

    @staticmethod
    def _py_filename(method: str, path: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9]", "_", path.strip("/"))
        slug = re.sub(r"_+", "_", slug).strip("_").lower()
        return f"test_{method.lower()}_{slug}.py"

    # ─── 代码生成 ─────────────────────────────────────────────────────────────

    def _generate_file_code(self, doc: dict, case_file_rel: str) -> str:
        endpoint = doc["endpoint"]
        method   = endpoint["method"]
        path     = endpoint["path"]
        feature  = endpoint.get("feature")
        cases    = doc["cases"]

        func_name = self._func_name(method, path)
        ids_list  = repr([c["id"] for c in cases])

        lines = [
            '"""',
            f"API 测试 - 自动生成",
            f"端点: {method} {path}",
            f"来源: {case_file_rel}",
            '"""',
            "from pathlib import Path",
            "import pytest",
            "from faker import Faker",
            "from utils.case_loader import load_yaml_cases",
            "",
            "_faker    = Faker('zh_CN')",
            f"_DATA     = load_yaml_cases(Path(__file__).parent.parent / 'cases' / '{Path(case_file_rel).name}')",
            "_ENDPOINT = _DATA['endpoint']",
            "_CASES    = _DATA['cases']",
            "",
            "",
        ]

        # @requires_feature mark（若端点属于特定功能）
        if feature:
            lines.append(f'@pytest.mark.requires_feature("{feature}")')

        # @parametrize
        lines += [
            f"@pytest.mark.parametrize('case', _CASES, ids={ids_list})",
            f"def {func_name}(api_client, case):",
            f'    """{method} {path}"""',
            "",
            "    # ── Token 处理（不重新登录，复用 session token）──────────────",
            "    need_token = case.get('need_token', _ENDPOINT['need_token'])",
            "    if need_token:",
            "        api_client.set_auth_token(api_client._cached_token)",
            "    else:",
            "        api_client.clear_auth()",
            "",
            "    # ── 动态数据注入（Faker）─────────────────────────────────────",
            "    body = dict(case['request'].get('body') or {})",
            "    for _f, _p in (case['request'].get('faker_fields') or {}).items():",
            "        body[_f] = getattr(_faker, _p)()",
            "",
            "    # ── 发送请求 ─────────────────────────────────────────────────",
            "    # YAML headers 含 tenant / locale 等非鉴权业务头，需要一并发送",
            "    _extra_headers = _DATA.get('headers') or {}",
            "    path = case['request'].get('path') or _ENDPOINT['path']",
            "    response = api_client.send_request(",
            f"        method=_ENDPOINT['method'],",
            "        url=path,",
            "        json=body or None,",
            "        headers=_extra_headers or None,",
            "    )",
            "",
            "    # ── 断言 ─────────────────────────────────────────────────────",
            "    api_client.assert_status_code(response, case['expect']['status'])",
            "    if 'response_time_ms' in case['expect']:",
            "        api_client.assert_response_time(response, case['expect']['response_time_ms'])",
            "    if case['expect'].get('json_not_null'):",
            "        assert response.json() is not None",
        ]

        return "\n".join(lines) + "\n"

    # ─── 公开接口 ─────────────────────────────────────────────────────────────

    def generate_from_yaml_file(self, yaml_file: Union[str, Path]) -> str:
        """从单个 YAML 生成一个 pytest 文件，返回生成路径"""
        yaml_path = Path(yaml_file)
        with open(yaml_path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)

        if not doc or "endpoint" not in doc:
            logger.warning(f"跳过无效 YAML: {yaml_path}")
            return ""

        endpoint = doc["endpoint"]
        out_name = self._py_filename(endpoint["method"], endpoint["path"])
        out_path = self.output_dir / out_name

        code = self._generate_file_code(doc, yaml_path.name)
        out_path.write_text(code, encoding="utf-8")
        logger.info(f"已生成: {out_path} ({len(doc.get('cases', []))} 条用例)")
        return str(out_path)

    def generate_from_yaml_dir(self, cases_dir: Union[str, Path]) -> List[str]:
        """扫描目录下所有 .yaml 文件并生成 pytest 脚本，返回生成路径列表"""
        cases_path = Path(cases_dir)
        yaml_files = sorted(cases_path.glob("*.yaml"))

        if not yaml_files:
            logger.warning(f"目录中没有 .yaml 文件: {cases_path}")
            return []

        written = []
        for yf in yaml_files:
            result = self.generate_from_yaml_file(yf)
            if result:
                written.append(result)

        logger.info(f"共生成 {len(written)} 个测试文件")
        return written
