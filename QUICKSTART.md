# 快速开始指南

## 🚀 5分钟快速上手

### 1. 安装

```bash
cd /Users/jiahua/.gemini/antigravity/scratch/playwright-test-framework

# 激活虚拟环境
source venv/bin/activate

# 如果还没安装依赖,运行:
# pip install -r requirements.txt
# playwright install chromium
```

### 2. 第一个 API 测试

创建 `tests/api/test_my_api.py`:

```python
import pytest

@pytest.mark.api
class TestMyAPI:
    def test_simple_get(self, api_client):
        # 发送请求
        response = api_client.get("https://api.github.com/users/github")
        
        # 断言
        api_client.assert_status_code(response, 200)
        api_client.assert_json_contains(response, {"login": "github"})
```

运行测试:
```bash
pytest tests/api/test_my_api.py -v
```

### 3. 第一个 UI 测试(带请求拦截)

创建 `tests/ui/test_my_ui.py`:

```python
import pytest
from base.ui_test_base import UITestBase

@pytest.mark.ui
class TestMyUI(UITestBase):
    def test_visit_page(self):
        # 导航
        self.navigate("https://example.com")
        
        # 验证
        assert "Example Domain" in self.get_text("h1")
        
        # 截图
        self.take_screenshot("example_page")
```

运行测试:
```bash
pytest tests/ui/test_my_ui.py -v
```

### 4. 使用请求拦截

修改 `config/config.yaml`:

```yaml
interception:
  enabled: true
  hosts:
    - api.yourapp.com  # 替换为你的 API host
```

运行 UI 测试后,拦截的请求会保存在 `data/requests/` 目录。

### 5. 从拦截请求生成 API 测试

```bash
# 查看拦截的请求文件
ls -la data/requests/

# 生成 API 测试
python generate_api_tests.py data/requests/requests_xxx.json

# 运行生成的测试
pytest tests/api/generated/ -v
```

### 6. 生成测试报告

```bash
# API 测试报告(自动生成时间戳命名,例如: 20251218_085911_API.html)
python run_tests.py api --report
open reports/api/20251218_085911_API.html

# UI 测试报告(自动生成时间戳命名,例如: 20251218_090000_UI.html)
python run_tests.py ui --report
open reports/ui/20251218_090000_UI.html
```

## 📋 常用命令

```bash
# 运行所有测试
pytest

# 运行特定标记的测试
pytest -m api
pytest -m ui
pytest -m smoke

# 并行运行
pytest -n 4

# 详细输出
pytest -v -s

# 只运行失败的测试
pytest --lf

# 生成覆盖率报告
pytest --cov=. --cov-report=html
```

## 🔧 配置你的项目

### 修改 API Base URL

编辑 `config/config.yaml`:
```yaml
api:
  base_url: https://your-api.com
```

或使用环境变量:
```bash
export API_BASE_URL=https://your-api.com
```

### 修改浏览器设置

```yaml
browser:
  type: chromium  # 或 firefox, webkit
  headless: false  # true 为无头模式
  viewport:
    width: 1920
    height: 1080
```

### 配置拦截规则

```yaml
interception:
  enabled: true
  hosts:
    - api.example.com
    - another-api.com
  deduplicate: true  # 去重
  ignore_resource_types:
    - image
    - stylesheet
    - font
```

## 💡 实用技巧

### 1. 使用环境变量

创建 `.env` 文件:
```bash
cp .env.example .env
```

编辑 `.env`:
```
API_BASE_URL=https://staging-api.com
HEADLESS=true
TEST_USERNAME=test_user
TEST_PASSWORD=test_pass
```

### 2. 参数化测试

```python
@pytest.mark.parametrize("user_id,expected_name", [
    (1, "Alice"),
    (2, "Bob"),
    (3, "Charlie")
])
def test_users(api_client, user_id, expected_name):
    response = api_client.get(f"/users/{user_id}")
    api_client.assert_json_contains(response, {"name": expected_name})
```

### 3. 使用 fixtures

在 `tests/conftest.py` 添加:
```python
@pytest.fixture
def auth_token():
    return "your-auth-token"

@pytest.fixture
def test_user():
    return {"username": "test", "password": "pass"}
```

### 4. 调试技巧

```python
# 在测试中添加断点
import pdb; pdb.set_trace()

# 查看页面 HTML
print(self.page.content())

# 等待调试
import time; time.sleep(10)
```

## 📚 更多资源

- [README.md](file:///Users/jiahua/.gemini/antigravity/scratch/playwright-test-framework/README.md) - 完整文档
- [USAGE.md](file:///Users/jiahua/.gemini/antigravity/scratch/playwright-test-framework/USAGE.md) - 详细使用指南
- [Playwright 官方文档](https://playwright.dev/python/)
- [Pytest 官方文档](https://docs.pytest.org/)

## ❓ 遇到问题?

1. 检查日志: `logs/test.log`
2. 查看截图: `reports/screenshots/`
3. 启用详细日志: 在 `config.yaml` 中设置 `logging.level: DEBUG`
4. 关闭无头模式查看浏览器操作: `headless: false`
