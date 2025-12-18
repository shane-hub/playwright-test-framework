# 使用指南

## 快速命令

### 安装和设置

```bash
# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install chromium

# 复制环境变量配置
cp .env.example .env
```

### 运行测试

```bash
# 使用测试运行器
python run_tests.py ui          # 运行 UI 测试
python run_tests.py api         # 运行 API 测试
python run_tests.py all         # 运行所有测试

# 生成报告
python run_tests.py ui --report
python run_tests.py api --report

# 并行运行
python run_tests.py all --parallel 4

# 无头模式
python run_tests.py ui --headless

# 直接使用 pytest
pytest -m ui                    # 只运行 UI 测试
pytest -m api                   # 只运行 API 测试
pytest -m smoke                 # 只运行冒烟测试
pytest tests/ui/test_example_ui.py  # 运行特定文件
```

### 生成 API 测试用例

```bash
# 从拦截的请求生成测试用例
python generate_api_tests.py data/requests/requests_20231217_120000.json

# 指定输出文件名
python generate_api_tests.py data/requests/requests_latest.json -o test_my_api.py

# 指定输出目录
python generate_api_tests.py data/requests/requests_latest.json -d tests/api/custom/
```

## 配置修改

### 修改拦截的 host

编辑 `config/config.yaml`:

```yaml
interception:
  hosts:
    - your-api.com
    - another-api.com
```

### 修改浏览器类型

```yaml
browser:
  type: firefox  # chromium, firefox, webkit
```

### 修改 API base URL

```yaml
api:
  base_url: https://your-api.com
```

或使用环境变量:

```bash
export API_BASE_URL=https://your-api.com
```

## 编写测试

### UI 测试模板

```python
import pytest
from base.ui_test_base import UITestBase

@pytest.mark.ui
class TestMyFeature(UITestBase):
    def test_something(self):
        self.navigate("https://example.com")
        self.click("button#submit")
        self.wait_for_selector(".result")
        assert "Success" in self.get_text(".result")
```

### API 测试模板

```python
import pytest

@pytest.mark.api
class TestMyAPI:
    def test_endpoint(self, api_client):
        response = api_client.get("/endpoint")
        api_client.assert_status_code(response, 200)
        api_client.assert_json_contains(response, {"key": "value"})
```

## 常见问题

### Q: 如何查看拦截的请求?

A: 拦截的请求保存在 `data/requests/` 目录,以 JSON 格式存储。

### Q: 如何禁用请求拦截?

A: 在 `config/config.yaml` 中设置:

```yaml
interception:
  enabled: false
```

### Q: 如何在 CI/CD 中运行?

A: 使用无头模式:

```bash
export HEADLESS=true
python run_tests.py all --report
```

### Q: 如何调试测试?

A: 
1. 设置 `headless: false` 查看浏览器操作
2. 使用 `self.take_screenshot()` 截图
3. 查看日志文件 `logs/test.log`

## 目录说明

- `config/` - 配置文件
- `core/` - 核心功能模块
- `base/` - 测试基类
- `tests/ui/` - UI 测试用例
- `tests/api/` - API 测试用例
- `tests/api/generated/` - 自动生成的 API 测试
- `reports/` - 测试报告
- `data/requests/` - 拦截的请求数据
- `logs/` - 日志文件
- `utils/` - 工具函数
