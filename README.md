# Playwright UI + API 测试框架

一个基于 Python Playwright 的综合测试框架,支持 UI 自动化测试、API 请求拦截、自动生成 API 测试用例,以及分离的测试报告。

## 特性

- ✅ **UI 自动化测试**: 基于 Playwright 的强大 UI 测试能力
- 🔍 **请求拦截**: 自动拦截指定 host 的所有网络请求
- 🤖 **自动生成 API 用例**: 从拦截的请求自动生成可执行的 API 测试用例
- 📊 **分离报告**: UI 和 API 测试报告完全分离
- ⚙️ **配置化管理**: 所有配置集中在 YAML 文件中
- 🏢 **多商户支持**: 支持多商户配置隔离，通过命令行参数灵活切换运行环境
- 🚀 **丰富功能**: 支持并行测试、失败重试、性能监控等

## 项目结构

```
playwright-test-framework/
├── config/              # 配置文件
│   └── config.yaml     # 主配置文件
├── core/               # 核心模块
│   ├── config_manager.py      # 配置管理器
│   ├── request_interceptor.py # 请求拦截器
│   └── api_generator.py       # API 用例生成器
├── base/               # 测试基类
│   ├── ui_test_base.py        # UI 测试基类
│   └── api_test_base.py       # API 测试基类
├── tests/              # 测试用例
│   ├── ui/            # UI 测试
│   └── api/           # API 测试
│       └── generated/ # 自动生成的 API 测试
├── reports/           # 测试报告
│   ├── ui/           # UI 测试报告
│   └── api/          # API 测试报告
├── data/             # 数据目录
│   ├── requests/     # 拦截的请求数据
│   └── test_data/    # 测试数据
└── utils/            # 工具模块
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境(推荐)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器
playwright install
```

### 2. 配置

编辑 `config/config.yaml` 配置文件:

```yaml
# 配置需要拦截的 host
interception:
  enabled: true
  hosts:
    - api.example.com
    - your-api-host.com

# 配置 API base URL
api:
  base_url: https://api.example.com
```

### 3. 运行测试

**🚀 智能测试流程(推荐)**

```bash
# 完整流程: UI测试 -> 检测API变化 -> 自动生成测试 -> API测试
python run_tests.py full

# 只运行 UI 测试
python run_tests.py ui

# 只运行 API 测试
python run_tests.py api

# 并行运行 + 无头模式
python run_tests.py full --headless --parallel 4

# 清空缓存,强制重新生成所有测试
python run_tests.py full --clear-cache
```

**传统方式(直接使用 pytest)**

```bash
# 运行所有测试
pytest

# 只运行 UI 测试
pytest -m ui

# 只运行 API 测试
pytest -m api

# 生成 HTML 报告
pytest tests/ui/ --html=reports/ui/report.html
pytest tests/api/ --html=reports/api/report.html

# 并行运行测试
pytest -n 4

# 指定商户运行测试 (自动加载商户对应的 API/UI URL 和拦截配置)
pytest --merchant=merchant_a

# 指定商户和环境
pytest --merchant=merchant_a --env=prod
```

## 使用指南

### UI 测试

继承 `UITestBase` 类创建 UI 测试:

```python
from base.ui_test_base import UITestBase
import pytest

@pytest.mark.ui
class TestMyUI(UITestBase):
    def test_login(self):
        # 导航到页面
        self.navigate("https://example.com/login")
        
        # 填充表单
        self.fill("input[name='username']", "test_user")
        self.fill("input[name='password']", "password")
        
        # 点击按钮
        self.click("button[type='submit']")
        
        # 等待元素
        self.wait_for_selector(".dashboard")
        
        # 截图
        self.take_screenshot("after_login")
```

### API 测试

使用 `api_client` fixture 进行 API 测试:

```python
import pytest

@pytest.mark.api
class TestMyAPI:
    def test_get_user(self, api_client):
        # 发送请求
        response = api_client.get("/users/1")
        
        # 断言
        api_client.assert_status_code(response, 200)
        api_client.assert_response_time(response, 1000)
        api_client.assert_json_contains(response, {"id": 1})
```

### 请求拦截

UI 测试会自动拦截配置的 host 请求,拦截的数据保存在 `data/requests/` 目录。

### 生成 API 测试用例

从拦截的请求生成 API 测试用例:

```python
from core.api_generator import APITestGenerator

generator = APITestGenerator()
generator.generate_from_file("data/requests/requests_20231217_120000.json")
```

或使用命令行:

```bash
python -c "from core.api_generator import APITestGenerator; \
           APITestGenerator().generate_from_file('data/requests/requests_latest.json')"
```

生成的测试用例位于 `tests/api/generated/` 目录。

### 多商户测试

支持使用 `@pytest.mark.merchant` 标记来控制测试用例适用的商户：

```python
import pytest

# 仅在 merchant_a 运行时执行
@pytest.mark.merchant("merchant_a")
def test_feature_exclusive_to_a():
    pass

# 在 merchant_a 或 merchant_b 运行时执行
@pytest.mark.merchant("merchant_a", "merchant_b")
def test_common_feature():
    pass
```

## 配置说明

### 浏览器配置

```yaml
browser:
  type: chromium        # chromium, firefox, webkit
  headless: false       # 是否无头模式
  slow_mo: 0           # 慢动作(毫秒)
  viewport:
    width: 1920
    height: 1080
```

### 拦截配置

```yaml
interception:
  enabled: true
  hosts:
    - api.example.com   # 需要拦截的 host
  deduplicate: true     # 是否去重
  ignore_resource_types:
    - image
    - stylesheet
```

### 多商户配置

在 `merchants` 节点下配置商户信息，支持区分 `test` 和 `prod` 环境：

```yaml
merchants:
  merchant_a:
    test:
      api_url: https://test-api.merchant-a.com
      ui_url: https://test.merchant-a.com
      username: user_a_test
      password: password_a_test
      interception_hosts:
        - test-api.merchant-a.com
    prod:
      api_url: https://api.merchant-a.com
      ui_url: https://merchant-a.com
      interception_hosts:
        - api.merchant-a.com
```

### 报告配置

```yaml
reports:
  ui:
    format: html
    output_dir: reports/ui    # 报告格式: YYYYMMDD_HHMMSS_UI.html
  api:
    format: html
    output_dir: reports/api   # 报告格式: YYYYMMDD_HHMMSS_API.html
```

## 高级功能

### 环境变量

支持使用环境变量覆盖配置:

```bash
export ENVIRONMENT=staging
export API_BASE_URL=https://staging-api.example.com
export HEADLESS=true
```

或使用 `.env` 文件:

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 并行测试

```bash
# 使用 4 个进程并行运行
pytest -n 4
```

### 失败重试

```bash
# 失败的测试重试 2 次
pytest --reruns 2
```

### 性能监控

框架会自动记录:
- 页面加载时间
- API 响应时间

配置性能阈值:

```yaml
performance:
  enabled: true
  thresholds:
    page_load_time: 3000   # ms
    api_response_time: 1000 # ms
```

## 最佳实践

1. **配置管理**: 将敏感信息放在 `.env` 文件中,不要提交到版本控制
2. **测试隔离**: 每个测试应该独立,不依赖其他测试
3. **使用标记**: 使用 pytest 标记组织测试(ui, api, smoke, regression)
4. **截图**: 在关键步骤截图,便于问题排查
5. **日志**: 充分利用日志记录测试过程
6. **数据驱动**: 使用参数化测试处理多组数据

## 故障排查

### Playwright 浏览器未安装

```bash
playwright install
```

### 请求未被拦截

检查 `config.yaml` 中的 `interception.hosts` 配置是否正确。

### 测试超时

调整 `config.yaml` 中的 `browser.timeout` 或 `api.timeout`。

## 贡献

欢迎提交 Issue 和 Pull Request!

## 许可证

MIT License
