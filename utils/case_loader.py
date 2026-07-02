"""
YAML 测试用例加载工具
供生成的 pytest 文件在运行时加载 cases
"""
from pathlib import Path
from typing import Any, Dict, Union

import yaml


def load_yaml_cases(case_file: Union[str, Path]) -> Dict[str, Any]:
    """
    加载 YAML case 文件，返回完整文档字典。

    用法（在生成的测试文件里）：
        _DATA = load_yaml_cases(Path(__file__).parent.parent / "cases" / "post_v1_login.yaml")
        _ENDPOINT = _DATA["endpoint"]

        @pytest.mark.parametrize("case", _DATA["cases"], ids=[c["id"] for c in _DATA["cases"]])
        def test_post_v1_login(api_client, case):
            ...
    """
    path = Path(case_file)
    if not path.exists():
        raise FileNotFoundError(f"Case 文件不存在: {path.resolve()}")

    with open(path, encoding="utf-8") as f:
        doc = yaml.safe_load(f)

    if not doc or "endpoint" not in doc or "cases" not in doc:
        raise ValueError(f"Case 文件格式不正确（缺少 endpoint 或 cases 字段）: {path}")

    return doc
