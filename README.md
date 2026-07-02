# Multi-Merchant Playwright Test Framework

> 一套代码，覆盖多个商户、多套环境的 UI + API 自动化测试框架。

---

## 这个框架解决什么问题？

假设你们有 6 个商户（merchant_1 ~ merchant_6），每个商户有 dev / staging / prod 三套环境。
传统做法要维护 6 × 3 = 18 套测试代码，任何改动都要同步 18 份，成本极高。

这个框架的目标是：
- **一套代码，全部覆盖** — 测试脚本只写一次，通过参数 `--merchant --env` 选择运行哪个
- **自动跳过不支持的功能** — merchant_2 不支持加密货币，跑 crypto 测试时自动 skip，不需要 if 判断
- **API 测试三步自动生成** — 用 Playwright 跑一遍 UI 流程，框架自动录制接口 → 生成测试用例 → 生成测试脚本
- **动态测试数据** — 每次运行自动生成随机姓名、手机号、银行卡号，避免数据冲突

---

## 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           测试执行层                                     │
│                                                                         │
│   pytest --merchant=merchant_1 --env=staging -n 4                      │
│        │                                                                │
│        ├── conftest.py ──── ConfigManager（读商户配置）                   │
│        │                       └── 环境变量（账号密码）                   │
│        │                                                                │
│        ├── UI 测试 ─────── Playwright 控制浏览器                          │
│        │   tests/ui/           └── RequestInterceptor（拦截 API 请求）   │
│        │                                                                │
│        └── API 测试 ────── APITestBase（发 HTTP 请求）                   │
│            tests/api/          ├── _session_token（整场只登录一次）       │
│            generated/          └── api_client（每条用例独立 session）     │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        三层流水线（API 测试生成）                          │
│                                                                         │
│  ┌─────────────┐     ┌──────────────────┐     ┌────────────────────┐  │
│  │  第一层      │     │  第二层           │     │  第三层             │  │
│  │  UI 录制    │────▶│  YAML Case 文件  │────▶│  pytest 脚本        │  │
│  │             │     │                  │     │                    │  │
│  │  跑 UI 测试  │     │  可以手动编辑！    │     │  自动生成，          │  │
│  │  框架自动    │     │  修改期望状态码、  │     │  包含正常/异常/      │  │
│  │  拦截接口    │     │  增删用例         │     │  边界三类用例        │  │
│  └─────────────┘     └──────────────────┘     └────────────────────┘  │
│         │                     │                        │               │
│  data/requests/         tests/api/cases/       tests/api/generated/    │
│  *.json                 *.yaml                 test_*.py               │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        多商户配置体系                                     │
│                                                                         │
│  config/merchants/                                                      │
│  ├── merchant_1.yaml ── features: {crypto: true, kyc3: true, ...}      │
│  ├── merchant_2.yaml ── features: {crypto: false, kyc3: true, ...}     │
│  └── merchant_3.yaml ── features: {crypto: true, kyc3: false, ...}     │
│                                                                         │
│  运行 merchant_2 时，所有带 @requires_feature("crypto") 的测试自动 skip   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构详解

```
playwright-test-framework/
│
├── conftest.py                  ← 【重要】全局 pytest 配置
│                                   定义所有 fixture（商户配置、token、页面、拦截器）
│                                   所有测试文件都能直接用这里的 fixture
│
├── generate_api_cases.py        ← 【CLI工具】第二层：JSON → YAML
│                                   读取录制的接口 JSON，生成带测试用例的 YAML
│
├── generate_api_tests.py        ← 【CLI工具】第三层：YAML → pytest
│                                   读取 YAML，生成可直接运行的 pytest 脚本
│
├── requirements.txt             ← 依赖清单
│
├── base/
│   ├── api_test_base.py         ← HTTP 客户端封装
│   │                               封装了 send_request / assert_status_code 等方法
│   │                               支持相对路径（/api/v1/login），自动拼接 base_url
│   └── ui_test_base.py          ← Playwright 基类（老用例兼容用，新用例直接用 fixture）
│
├── core/
│   ├── config_manager.py        ← 【核心】多商户配置管理
│   │                               读取 config/merchants/merchant_X.yaml
│   │                               读取环境变量里的账号密码
│   │                               同一 merchant+env 组合只有一个实例（单例）
│   │
│   ├── case_generator.py        ← 第二层核心：从拦截 JSON 生成 YAML
│   │                               自动判断是否需要 token（有 Authorization header）
│   │                               自动生成正常/异常/边界三类用例
│   │                               自动识别 phone/name 等字段，写入 faker_fields
│   │
│   ├── api_generator.py         ← 第三层核心：从 YAML 生成 pytest 脚本
│   │                               生成 @pytest.mark.parametrize 参数化测试
│   │                               运行时自动用 Faker 替换动态字段
│   │
│   └── request_interceptor.py   ← Playwright 请求拦截器
│                                   过滤图片/字体等静态资源
│                                   按 method+path 去重（同接口只保留一条）
│
├── utils/
│   ├── case_loader.py           ← YAML 加载工具（给生成的测试脚本用）
│   ├── helpers.py               ← 工具函数（目录创建、时间戳、JSON读写）
│   └── logger.py                ← 统一日志配置
│
├── config/
│   ├── config.yaml              ← 全局配置（浏览器参数、报告路径、日志级别）
│   └── merchants/
│       ├── merchant_1.yaml      ← 商户1：功能最全（含所有feature）
│       ├── merchant_2.yaml      ← 商户2：功能子集
│       ├── merchant_3.yaml
│       ├── merchant_4.yaml
│       ├── merchant_5.yaml
│       └── merchant_6.yaml
│
├── tests/
│   ├── conftest.py              ← 空文件（选项统一在根 conftest.py 注册）
│   ├── ui/                      ← UI 测试（手写）
│   └── api/
│       ├── cases/               ← 第二层产物：YAML case 文件
│       │   ├── post_api_v1_login.yaml
│       │   ├── get_api_v1_users_{id}.yaml
│       │   └── ...
│       └── generated/           ← 第三层产物：自动生成的 pytest 脚本
│           ├── test_post_api_v1_login.py
│           ├── test_get_api_v1_users_{id}.py
│           └── ...
│
├── data/
│   └── requests/                ← 第一层产物：UI 录制时拦截的接口 JSON
│       └── merchant_1_staging_master_requests.json
│
├── reports/
│   ├── html/                    ← HTML 测试报告
│   └── ui/                      ← 截图 / 录屏
│
└── .github/workflows/
    └── multi_merchant_ci.yml    ← GitHub Actions：6 商户并行跑
```

---

## 从零开始使用

### 第一步：安装依赖

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装 Playwright 浏览器内核（只需安装一次）
playwright install chromium
```

---

### 第二步：配置你的商户

每个商户对应 `config/merchants/` 下的一个 YAML 文件。

**示例：`config/merchants/merchant_1.yaml`**

```yaml
# ── 登录接口路径（不敏感，可以提交代码库）──────────────────────
credentials:
  login_path: "/api/v1/login"
  # 账号密码不写这里！通过环境变量注入（见下一步）

# ── 功能矩阵：声明这个商户支持哪些功能 ──────────────────────────
# true = 支持，false 或不写 = 不支持
# 带 @requires_feature("xxx") 的测试，在不支持的商户上自动 skip
features:
  kyc_level_3:    true   # KYC 三级认证
  crypto_payment: true   # 加密货币支付
  points_system:  true   # 积分系统
  live_betting:   true   # 实时投注
  multi_currency: true   # 多币种

# ── 各环境的 URL 配置 ────────────────────────────────────────────
environments:
  dev:
    api_url: "http://localhost:8001"     # 后端 API 地址
    web_url: "http://localhost:3001"     # 前端页面地址
  staging:
    api_url: "https://api-staging.merchant1.example.com"
    web_url: "https://staging.merchant1.example.com"
  prod:
    api_url: "https://api.merchant1.example.com"
    web_url: "https://merchant1.example.com"

# ── 请求拦截配置（UI 测试时录制 API 接口用）────────────────────────
interception:
  enabled: true
  deduplicate: true        # 同一个接口只保留一条记录
  ignore_resource_types: [image, stylesheet, font, media]  # 过滤静态资源
  requests_dir: "data/requests"
  # hosts 不填则自动从 api_url 推断
  hosts:
    - "localhost:8001"
    - "api-staging.merchant1.example.com"
```

**配置不同功能的商户**：merchant_2 如果不支持加密货币，只需把 `crypto_payment: false` 或直接删掉该行即可。

---

### 第三步：设置账号密码（环境变量）

账号密码**绝对不能写进 YAML 文件**，通过环境变量注入。

**命名规则**：`商户名（大写）__环境名（大写）__USERNAME / PASSWORD`

```
MERCHANT_1__DEV__USERNAME      = admin
MERCHANT_1__DEV__PASSWORD      = dev_password_123
MERCHANT_1__STAGING__USERNAME  = qa_admin
MERCHANT_1__STAGING__PASSWORD  = staging_password
MERCHANT_2__STAGING__USERNAME  = m2_qa_admin
MERCHANT_2__STAGING__PASSWORD  = m2_staging_pass
```

**本地开发** — 在项目根目录创建 `.env` 文件：

```bash
# .env（加进 .gitignore，不要提交！）
MERCHANT_1__DEV__USERNAME=admin
MERCHANT_1__DEV__PASSWORD=dev_password_123
MERCHANT_1__STAGING__USERNAME=qa_admin
MERCHANT_1__STAGING__PASSWORD=staging_password
```

框架启动时会自动读取 `.env`，无需手动 `export`。

**CI 环境（GitHub Actions）** — 在仓库 Settings → Secrets and variables → Actions 里添加，名字与上面格式相同。

---

### 第四步：写 UI 测试并录制 API（第一层）

UI 测试放在 `tests/ui/` 目录下，用 pytest 函数写，通过 fixture 获取页面对象：

```python
# tests/ui/test_login.py

def test_user_login(page, merchant_cfg):
    """
    page      - Playwright Page 对象，框架自动创建并打开 web_url
    merchant_cfg - 当前商户配置，可以读取 URL、功能开关等
    """
    # 导航到登录页
    page.goto(merchant_cfg.web_url + "/login")

    # 填写表单
    page.fill("#username", "test_user")
    page.fill("#password", "test_pass")
    page.click("button[type='submit']")

    # 断言登录成功
    page.wait_for_url("**/dashboard", timeout=10000)
    assert page.title() == "Dashboard"
```

**运行 UI 测试，同时录制 API 请求**：

```bash
pytest tests/ui/ --merchant=merchant_1 --env=staging -v
```

运行完后，框架自动把拦截到的 API 请求保存到：

```
data/requests/merchant_1_staging_master_requests.json
```

这个 JSON 文件长这样：

```json
{
  "requests": [
    {
      "method": "POST",
      "url": "https://api-staging.merchant1.example.com/api/v1/login",
      "headers": { "Content-Type": "application/json" },
      "body": { "username": "test_user", "password": "test_pass" },
      "response": { "status": 200, "body": { "token": "eyJ..." } }
    },
    {
      "method": "GET",
      "url": "https://api-staging.merchant1.example.com/api/v1/users/123",
      "headers": { "Authorization": "Bearer eyJ..." },
      "response": { "status": 200, "body": { "id": 123, "name": "张三" } }
    }
  ]
}
```

---

### 第五步：生成 YAML 测试用例（第二层）

把录制的 JSON 转换成有组织的测试用例 YAML：

```bash
python generate_api_cases.py data/requests/merchant_1_staging_master_requests.json
```

每个接口生成一个 YAML 文件，放在 `tests/api/cases/` 目录：

```
tests/api/cases/
├── post_api_v1_login.yaml
├── get_api_v1_users_{id}.yaml
├── post_api_v1_orders.yaml
└── ...
```

**生成的 YAML 内容示例（`post_api_v1_login.yaml`）**：

```yaml
endpoint:
  method: POST
  path: /api/v1/login
  need_token: false     # 登录接口不需要 token，框架自动从 header 判断
  feature: null         # 不属于特定功能模块，所有商户都跑

headers:
  Content-Type: application/json

cases:
  # ── 正常用例：用录制的原始请求 ──────────────────────────────────
  - id: TC_001
    name: 正常登录
    type: normal
    priority: P0
    request:
      body:
        username: test_user    # 占位值，运行时被 Faker 替换为随机用户名
        password: test_pass    # 占位值，运行时被 Faker 替换为随机密码
      faker_fields:            # ← 框架自动识别的 Faker 字段
        username: user_name    # 每次运行生成不同用户名
        password: password     # 每次运行生成不同密码
    expect:
      status: 200
      response_time_ms: 3000   # 断言响应时间 < 3秒
      json_not_null: true      # 断言返回体不为空

  # ── 异常用例：缺少必填字段 ──────────────────────────────────────
  - id: TC_002
    name: '[异常] 缺少字段 username'
    type: abnormal
    priority: P1
    request:
      body:
        password: test_pass    # 没有 username
    expect:
      status: 400              # 期望返回 400 Bad Request

  - id: TC_003
    name: '[异常] 缺少字段 password'
    type: abnormal
    priority: P1
    request:
      body:
        username: test_user    # 没有 password
    expect:
      status: 400

  # ── 边界用例：极端输入 ──────────────────────────────────────────
  - id: TC_004
    name: '[边界] username 为空字符串'
    type: boundary
    priority: P2
    request:
      body:
        username: ''
        password: test_pass
    expect:
      status: 400

  - id: TC_005
    name: '[边界] username 超长（256字符）'
    type: boundary
    priority: P2
    request:
      body:
        username: 'aaaa...（256个a）'
        password: test_pass
    expect:
      status: 400
```

> **YAML 是可以手动编辑的！** 如果某个字段是可选的，把对应用例的 `expect.status` 从 400 改成 200 即可。改完重新跑第三步生成脚本，不需要重新录制 UI。

**如果同一个接口在不同商户参数不同**，用 `--prefix` 区分：

```bash
# 商户1的 case
python generate_api_cases.py data/requests/merchant_1_staging_requests.json \
    --prefix m1

# 商户2的 case（字段不一样）
python generate_api_cases.py data/requests/merchant_2_staging_requests.json \
    --prefix m2
```

---

### 第六步：生成 pytest 测试脚本（第三层）

把 YAML 转换成可直接运行的 pytest 脚本：

```bash
# 生成 cases/ 目录下所有 yaml 对应的测试脚本
python generate_api_tests.py tests/api/cases/

# 只生成单个文件
python generate_api_tests.py tests/api/cases/post_api_v1_login.yaml
```

生成的脚本放在 `tests/api/generated/`，内容大概长这样：

```python
# tests/api/generated/test_post_api_v1_login.py
# ⚠️ 此文件自动生成，不要手动修改
# ⚠️ 如需修改测试逻辑，请编辑 tests/api/cases/post_api_v1_login.yaml 后重新生成

from pathlib import Path
import pytest
from faker import Faker
from utils.case_loader import load_yaml_cases

_faker    = Faker('zh_CN')
_DATA     = load_yaml_cases(Path(__file__).parent.parent / 'cases' / 'post_api_v1_login.yaml')
_ENDPOINT = _DATA['endpoint']
_CASES    = _DATA['cases']


@pytest.mark.parametrize('case', _CASES, ids=['TC_001', 'TC_002', 'TC_003', 'TC_004', 'TC_005'])
def test_post_api_v1_login(api_client, case):
    """POST /api/v1/login"""

    # Token 处理（根据 need_token 决定是否注入 session token）
    need_token = case.get('need_token', _ENDPOINT['need_token'])
    if need_token:
        api_client.set_auth_token(api_client._cached_token)
    else:
        api_client.clear_auth()

    # 动态数据注入：TC_001 的 username/password 每次运行都是随机值
    body = dict(case['request'].get('body') or {})
    for _f, _p in (case['request'].get('faker_fields') or {}).items():
        body[_f] = getattr(_faker, _p)()

    # 发请求
    path = case['request'].get('path') or _ENDPOINT['path']
    response = api_client.send_request(method=_ENDPOINT['method'], url=path, json=body or None)

    # 断言
    api_client.assert_status_code(response, case['expect']['status'])
    if 'response_time_ms' in case['expect']:
        api_client.assert_response_time(response, case['expect']['response_time_ms'])
    if case['expect'].get('json_not_null'):
        assert response.json() is not None
```

---

### 第七步：运行测试

**运行 API 测试**：

```bash
# 基础用法：指定商户和环境
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -v

# 并行执行（4 个 worker，速度提升 4 倍）
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -n 4

# 只跑正常用例（TC_001）
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -k "TC_001"

# 只跑异常用例
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -k "abnormal"

# 生成 HTML 报告
pytest tests/api/generated/ --merchant=merchant_1 --env=staging \
    --html=reports/html/merchant_1_staging.html --self-contained-html
```

**同时跑 UI + API**：

```bash
pytest tests/ --merchant=merchant_1 --env=staging -v
```

**运行全量测试（6 个商户）**：

```bash
# 逐个跑
for m in merchant_1 merchant_2 merchant_3 merchant_4 merchant_5 merchant_6; do
    pytest tests/api/generated/ --merchant=$m --env=staging -n 4
done

# 或者直接触发 GitHub Actions CI（自动并行跑所有商户）
git push origin main
```

---

## 一步完成：UI 录制 + 自动生成

如果第一次搭建流水线，可以一条命令完成录制 + 生成 YAML + 生成脚本：

```bash
pytest tests/ui/ --merchant=merchant_1 --env=staging --generate-tests
```

等价于手动执行：

```bash
# 第一步：录制
pytest tests/ui/ --merchant=merchant_1 --env=staging

# 第二步：生成 YAML
python generate_api_cases.py data/requests/merchant_1_staging_master_requests.json

# 第三步：生成脚本
python generate_api_tests.py tests/api/cases/
```

> **注意**：`--generate-tests` 不能和 `-n 4` 同时使用（多个 worker 同时写文件会冲突）。
> 录制时不要加 `-n`，生成完再加 `-n` 跑测试。

---

## 手写测试用例

自动生成的测试覆盖常见场景，复杂业务逻辑需要手写。

### 手写 API 测试

```python
# tests/api/test_order_flow.py

import pytest

@pytest.mark.requires_feature("live_betting")  # 只在支持实时投注的商户跑
def test_place_bet(api_client):
    """下注完整流程"""

    # api_client 已经自动配好了 base_url（来自 --merchant --env 参数）
    # 需要 token 的请求，先注入 session token（整场只登录一次，不重复登录）
    api_client.set_auth_token(api_client._cached_token)

    # 下注
    resp = api_client.post("/api/v1/bets", json={
        "match_id": 100,
        "amount": 50,
        "odds": 1.8,
    })
    api_client.assert_status_code(resp, 201)
    api_client.assert_response_time(resp, 2000)  # 断言 < 2秒

    bet_id = resp.json()["id"]

    # 查询下注结果
    resp2 = api_client.get(f"/api/v1/bets/{bet_id}")
    api_client.assert_status_code(resp2, 200)
    api_client.assert_json_contains(resp2, {"status": "pending"})
```

### 手写 UI 测试

```python
# tests/ui/test_deposit.py

import pytest

@pytest.mark.requires_feature("crypto_payment")
def test_crypto_deposit(page, merchant_cfg, api_client):
    """加密货币充值 UI 流程"""

    # page 已经自动打开了 merchant_cfg.web_url，直接操作
    page.goto(merchant_cfg.web_url + "/deposit")

    # 选择加密货币
    page.click("[data-testid='crypto-tab']")
    page.select_option("#currency", "USDT")
    page.fill("#amount", "100")
    page.click("#submit-deposit")

    # 断言出现二维码
    page.wait_for_selector("[data-testid='qr-code']", timeout=5000)
    assert page.is_visible("[data-testid='qr-code']")
```

### 参数化多个商户场景

```python
# tests/api/test_currency.py

import pytest

@pytest.mark.requires_feature("multi_currency")
@pytest.mark.parametrize("currency", ["USD", "EUR", "CNY"])
def test_balance_by_currency(api_client, merchant_cfg, currency):
    """多币种余额查询"""

    # 只有 currencies 列表里有这个币种才跑
    supported = merchant_cfg.get("currencies", [])
    if currency not in supported:
        pytest.skip(f"{merchant_cfg.merchant} 不支持币种 {currency}")

    api_client.set_auth_token(api_client._cached_token)
    resp = api_client.get(f"/api/v1/balance?currency={currency}")
    api_client.assert_status_code(resp, 200)
```

---

## 商户功能矩阵速查

| 功能 | merchant_1 | merchant_2 | merchant_3 | merchant_4 | merchant_5 | merchant_6 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| kyc_level_3 | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| crypto_payment | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ |
| points_system | ✅ | ✅ | ✅ | ❌ | ❌ | ✅ |
| live_betting | ✅ | ❌ | ❌ | ✅ | ✅ | ❌ |
| multi_currency | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |

> 根据实际商户情况修改 `config/merchants/merchant_N.yaml` 中的 `features` 字段。

---

## CI/CD 自动化

推送代码后，GitHub Actions 自动对 6 个商户并行跑测试。

**`.github/workflows/multi_merchant_ci.yml`** 已配置好：

```
push 到 main/develop
    ↓
同时启动 6 个 Job（每个商户一个）
    merchant_1/staging    merchant_2/staging    merchant_3/staging
    merchant_4/staging    merchant_5/staging    merchant_6/staging
        ↓                     ↓                     ↓
    各自独立跑              各自独立跑              各自独立跑
    -n 4 并行              -n 4 并行              -n 4 并行
        ↓
    HTML 报告上传到 Artifacts（保留 7 天）
```

**在 GitHub 仓库 Settings → Secrets and variables → Actions 里添加以下 Secrets**：

```
MERCHANT_1__STAGING__USERNAME    = merchant1 的测试账号
MERCHANT_1__STAGING__PASSWORD    = merchant1 的测试密码
MERCHANT_2__STAGING__USERNAME    = merchant2 的测试账号
MERCHANT_2__STAGING__PASSWORD    = merchant2 的测试密码
...（每个商户都要配）
```

**手动触发某一个商户**：
在 GitHub → Actions → Multi-Merchant Test Matrix → Run workflow，选择商户和环境。

---

## Faker 动态数据说明

生成 YAML 时，框架自动识别字段名并注入 Faker，正常用例每次运行都有随机数据：

| 字段名（支持模糊匹配） | 生成的数据类型 | 示例 |
|---|---|---|
| `name` / `real_name` / `full_name` | 中文姓名 | 王芳、李建国 |
| `username` / `nickname` | 用户名 | zhangwei123 |
| `email` | 邮箱 | li_wei@example.com |
| `phone` / `mobile` / `tel` | 手机号 | 13812345678 |
| `bank_card` / `card_number` / `card_no` | 卡号 | 4532015112830366 |
| `id_card` / `id_no` / `id_number` | 身份证号 | |
| `address` | 地址 | 广东省广州市天河区... |
| `city` / `province` | 城市/省份 | 上海市 / 浙江省 |
| `password` / `passwd` | 密码 | Kd#9mN2p |
| `company` | 公司名 | 天龙科技有限公司 |
| `remark` / `description` | 随机句子 | |

> 模糊匹配规则：`user_phone` 包含 `phone` → 自动识别为 `phone_number`
>
> 自定义映射：在 `core/case_generator.py` 顶部的 `_FAKER_FIELD_MAP` 添加：
> ```python
> "member_name": "name",
> "contact_mobile": "phone_number",
> ```

---

## 常见问题

**Q：第一次使用，完整流程是什么？**

```
1. pip install -r requirements.txt && playwright install chromium
2. 编辑 config/merchants/merchant_1.yaml（填入你的 URL 和功能开关）
3. 创建 .env 文件，填入账号密码
4. 写 UI 测试放进 tests/ui/
5. pytest tests/ui/ --merchant=merchant_1 --env=dev -v  （运行并录制接口）
6. python generate_api_cases.py data/requests/merchant_1_dev_master_requests.json
7. 检查并调整 tests/api/cases/*.yaml（核对期望状态码）
8. python generate_api_tests.py tests/api/cases/
9. pytest tests/api/generated/ --merchant=merchant_1 --env=dev -v
```

---

**Q：不想录制 UI，直接写 API 测试可以吗？**

可以。有两种方式：

方式一：手写 YAML，再生成脚本
```bash
# 手写 tests/api/cases/post_api_v1_login.yaml
# 然后
python generate_api_tests.py tests/api/cases/post_api_v1_login.yaml
```

方式二：直接写 pytest 文件
```python
# tests/api/test_xxx.py
def test_something(api_client):
    resp = api_client.post("/api/v1/xxx", json={...})
    api_client.assert_status_code(resp, 200)
```

---

**Q：新增一个接口的 API 测试，不想重新录制 UI 怎么办？**

直接在 `tests/api/cases/` 下新建或编辑一个 YAML 文件，然后重新生成脚本：
```bash
python generate_api_tests.py tests/api/cases/新接口.yaml
```

---

**Q：边界用例期望 400，但接口对这个字段是可选的，实际返回 200？**

手动编辑对应 YAML，把 `expect.status: 400` 改为 `expect.status: 200`，重新生成脚本即可。

---

**Q：两个商户的同一个接口字段不一样，怎么分开管理？**

生成时加 `--prefix` 区分：
```bash
python generate_api_cases.py data/requests/merchant_1_staging.json --prefix m1
python generate_api_cases.py data/requests/merchant_2_staging.json --prefix m2
# 生成: m1_post_api_v1_login.yaml, m2_post_api_v1_login.yaml
```

---

**Q：并行跑测试时 session 之间会互相干扰吗？**

不会。每个 worker 有独立的 session token（各自登录一次），api_client 是 function 级别的 fixture，每条用例之间完全隔离。

---

**Q：如何只跑某个优先级的用例？**

```bash
# 只跑 P0（正常用例）
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -k "TC_001"

# 跑 P0 + P1（正常 + 异常）
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -k "normal or abnormal"
```

---

**Q：如何查看详细的请求和响应日志？**

```bash
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -v --log-cli-level=DEBUG
```
