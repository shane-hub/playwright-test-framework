# Multi-Merchant Playwright Test Framework

多商户自动化测试框架，支持 UI + API 集成测试，单份代码覆盖 6 个商户 × N 个环境。

---

## 目录结构

```
playwright-test-framework/
├── conftest.py                    # 全局 fixture：商户配置、token、拦截器、页面
├── requirements.txt
├── generate_api_cases.py          # CLI：JSON → YAML case（第二层）
├── generate_api_tests.py          # CLI：YAML case → pytest 脚本（第三层）
│
├── base/
│   ├── api_test_base.py           # HTTP 客户端封装（requests）
│   └── ui_test_base.py            # Playwright 基类（兼容老用例）
│
├── core/
│   ├── config_manager.py          # 多商户配置单例（merchant × env）
│   ├── case_generator.py          # 拦截 JSON → YAML case（自动生成规则）
│   ├── api_generator.py           # YAML case → pytest 脚本
│   └── request_interceptor.py     # Playwright 请求拦截 & 去重
│
├── utils/
│   ├── case_loader.py             # YAML 文件加载（供生成的脚本运行时使用）
│   ├── helpers.py                 # ensure_dir / get_timestamp / load_json
│   └── logger.py                  # 统一日志
│
├── config/
│   ├── config.yaml                # 全局配置（浏览器、报告、日志）
│   └── merchants/
│       ├── merchant_1.yaml        # 商户1配置（功能矩阵 + 各环境 URL）
│       ├── merchant_2.yaml
│       └── ...                    # merchant_3 ~ merchant_6
│
├── tests/
│   ├── ui/                        # UI 测试（手写）
│   └── api/
│       ├── cases/                 # YAML case 文件（generate_api_cases.py 生成）
│       └── generated/             # pytest 脚本（generate_api_tests.py 生成）
│
├── data/
│   └── requests/                  # 拦截保存的原始 JSON
│
├── reports/
│   ├── html/                      # pytest-html 报告
│   └── ui/                        # 截图 / 视频
│
└── .github/workflows/
    └── multi_merchant_ci.yml      # 6 商户并行 CI
```

---

## 核心概念

### 三层流水线

```
[第一层]  UI 测试录制
          pytest tests/ui/ --merchant=merchant_1 --env=staging
               ↓ 拦截 API 请求 → data/requests/merchant_1_staging_master_requests.json

[第二层]  生成 YAML case
          python generate_api_cases.py data/requests/merchant_1_staging_master_requests.json
               ↓ → tests/api/cases/post_api_v1_login.yaml
                    tests/api/cases/get_api_v1_users_{id}.yaml ...

[第三层]  生成 pytest 脚本
          python generate_api_tests.py tests/api/cases/
               ↓ → tests/api/generated/test_post_api_v1_login.py
                    tests/api/generated/test_get_api_v1_users_{id}.py ...
```

YAML 是**可编辑的中间层**：第一次生成后，手动调整 YAML（修改期望状态码、补充边界值等），重新运行第三步即可更新脚本，无需重新录制。

---

### 功能矩阵与自动跳过

每个商户 YAML 声明支持哪些功能：

```yaml
# config/merchants/merchant_1.yaml
features:
  kyc_level_3:    true
  crypto_payment: true
  live_betting:   true
```

测试用例用 `@pytest.mark.requires_feature` 标注：

```python
@pytest.mark.requires_feature("crypto_payment")
@pytest.mark.parametrize("case", _CASES)
def test_post_api_v1_crypto_deposit(api_client, case):
    ...
```

不支持该功能的商户运行时自动 `skip`，无需修改测试代码。

---

### Token 管理策略

```
Session 开始
    ↓
_session_token fixture（scope=session）
    └─ 每个 worker 只登录 1 次，token 缓存在内存
         ↓
api_client fixture（scope=function）
    └─ 每条用例创建新 HTTP session，避免状态污染
    └─ client._cached_token = _session_token（不自动注入）
         ↓
用例按需注入：
    need_token=True  → api_client.set_auth_token(api_client._cached_token)
    need_token=False → api_client.clear_auth()
```

pytest-xdist `-n 4`：4 个 worker 各登录 1 次，总登录次数 = 4，不是用例数。

---

### 动态测试数据（Faker）

`case_generator` 自动识别 body 字段名 → 在 **TC_001 正常用例** 写入 `faker_fields`：

| 字段名（含模糊匹配） | Faker Provider |
|---|---|
| name / real_name / full_name | `name`（中文姓名） |
| username / nickname | `user_name` |
| email | `email` |
| phone / mobile / tel | `phone_number` |
| bank_card / card_number / card_no | `credit_card_number` |
| id_card / id_no / id_number | `ssn`（身份证） |
| address | `address` |
| city / province | `city` / `province` |
| password / passwd | `password` |
| company | `company` |
| remark / description / desc | `sentence` |

异常/边界用例使用固定值，不受 Faker 影响。

自定义映射（在 `core/case_generator.py` 顶部 `_FAKER_FIELD_MAP` 里添加）：
```python
"member_name": "name",
"contact_mobile": "phone_number",
```

---

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置商户

复制并编辑商户配置：

```bash
cp config/merchants/merchant_1.yaml config/merchants/merchant_2.yaml
# 修改 features、environments 下的 api_url / web_url
```

### 3. 设置账号密码

**本地开发** — 创建 `.env` 文件（不要提交到 git）：

```env
MERCHANT_1__DEV__USERNAME=admin
MERCHANT_1__DEV__PASSWORD=secret123
MERCHANT_1__STAGING__USERNAME=qa_admin
MERCHANT_1__STAGING__PASSWORD=stagingpass
```

**CI / GitHub Actions** — 在仓库 Settings → Secrets 里添加（格式相同）。

命名规则：`{MERCHANT}__{ENV}__{USERNAME|PASSWORD}`，双下划线分隔。

### 4. 录制 UI 测试（第一层）

```bash
# 跑 UI 测试，自动拦截 API 请求
pytest tests/ui/ --merchant=merchant_1 --env=staging -v

# 跑完后查看拦截结果
ls data/requests/
# → merchant_1_staging_master_requests.json
```

### 5. 生成 YAML case（第二层）

```bash
python generate_api_cases.py data/requests/merchant_1_staging_master_requests.json

# 指定输出目录或加前缀
python generate_api_cases.py data/requests/merchant_1_staging_master_requests.json \
    --output-dir tests/api/cases \
    --prefix m1_stg
```

生成的 YAML 示例（`tests/api/cases/post_api_v1_login.yaml`）：

```yaml
endpoint:
  method: POST
  path: /api/v1/login
  need_token: false
  feature: null

headers:
  Content-Type: application/json

cases:
  - id: TC_001
    name: 正常请求
    type: normal
    priority: P0
    request:
      body:
        username: admin
        password: secret
      faker_fields:          # 运行时被 Faker 动态替换
        username: user_name
        password: password
    expect:
      status: 200
      response_time_ms: 3000
      json_not_null: true

  - id: TC_002
    name: '[异常] 缺少字段 username'
    type: abnormal
    priority: P1
    request:
      body:
        password: secret
    expect:
      status: 400

  - id: TC_003
    name: '[边界] username 为空字符串'
    type: boundary
    priority: P2
    request:
      body:
        username: ''
        password: secret
    expect:
      status: 400
```

**手动调整 YAML** — 可以修改 `expect.status`、增删用例、改字段值，改完重新跑第三步即可。

### 6. 生成 pytest 脚本（第三层）

```bash
# 生成目录下全部 yaml
python generate_api_tests.py tests/api/cases/

# 生成单个
python generate_api_tests.py tests/api/cases/post_api_v1_login.yaml

# 查看生成结果
ls tests/api/generated/
# → test_post_api_v1_login.py
```

### 7. 运行 API 测试

```bash
# 单商户单环境
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -v

# 并行 4 workers
pytest tests/api/generated/ --merchant=merchant_1 --env=staging -n 4

# 指定用例 ID
pytest tests/api/generated/ -k "TC_001"

# 只跑正常用例
pytest tests/api/generated/ -k "TC_001"

# 生成 HTML 报告
pytest tests/api/generated/ --merchant=merchant_1 --env=staging \
    --html=reports/html/merchant_1_staging.html --self-contained-html
```

---

## 一步到位（UI 完成后自动生成）

```bash
# 跑 UI + 自动生成 YAML + 自动生成脚本
pytest tests/ui/ --merchant=merchant_1 --env=dev \
    --generate-tests

# 只生成 YAML（不生成脚本）
pytest tests/ui/ --merchant=merchant_1 --env=dev \
    --generate-cases
```

> **注意**：`--generate-cases / --generate-tests` 在 xdist（`-n 4`）模式下会跳过自动生成并打印提示，需手动运行 CLI 脚本。原因：多 worker 并发写同一批文件会产生冲突。

---

## CI/CD

`.github/workflows/multi_merchant_ci.yml` 已配置 6 商户并行矩阵：

- `fail-fast: false`：单商户失败不阻断其余商户
- 每个 Job 使用 `-n 4` 并行
- 报告上传到 Artifacts（保留 7 天）

**触发方式：**

| 触发 | 说明 |
|---|---|
| push to main/develop | 自动运行所有商户 staging 环境 |
| PR to main | 自动运行 |
| workflow_dispatch | 手动触发，可指定单商户 / 环境 |

**GitHub Secrets 命名规则：**

```
MERCHANT_1_STAGING_USERNAME
MERCHANT_1_STAGING_PASSWORD
MERCHANT_1_STAGING_API_URL    （可选，覆盖 yaml 里的 api_url）
MERCHANT_2_STAGING_USERNAME
...
```

---

## 商户配置参考

`config/merchants/merchant_1.yaml`（完整字段说明）：

```yaml
# 登录路径（非敏感，可提交）
credentials:
  login_path: "/api/v1/login"
  # username / password 通过环境变量注入，不写这里

# 功能矩阵（true=支持，false/缺省=不支持）
features:
  kyc_level_3:    true
  crypto_payment: true
  points_system:  true
  live_betting:   true
  multi_currency: true

# 商户业务参数（供测试用例参数化使用）
max_bet:      10000
min_bet:      10
currencies:   [USD, EUR, CNY, USDT]

# 请求拦截配置
interception:
  enabled:              true
  deduplicate:          true         # 同接口只保留一条（优先 2xx）
  ignore_resource_types: [image, stylesheet, font, media]
  requests_dir:         "data/requests"
  hosts:                             # 留空则从 api_url 自动推断
    - "localhost:8001"
    - "api-staging.merchant1.example.com"

# 各环境配置
environments:
  dev:
    api_url: "http://localhost:8001"
    web_url: "http://localhost:3001"
  staging:
    api_url: "https://api-staging.merchant1.example.com"
    web_url: "https://staging.merchant1.example.com"
  prod:
    api_url: "https://api.merchant1.example.com"
    web_url: "https://merchant1.example.com"
```

---

## 编写测试用例

### API 测试（生成的脚本，无需手写）

```python
# tests/api/generated/test_post_api_v1_login.py（自动生成，不要手动修改）
# 手动改需求请编辑 tests/api/cases/post_api_v1_login.yaml 后重新生成
```

### 手写 API 测试

```python
def test_create_order(api_client, merchant_cfg):
    api_client.set_auth_token(api_client._cached_token)
    resp = api_client.post("/api/v1/orders", json={
        "amount": 100,
        "currency": "USD",
    })
    api_client.assert_status_code(resp, 201)
    api_client.assert_json_contains(resp, {"status": "pending"})
```

### UI 测试

```python
def test_login_page(page, merchant_cfg):
    page.goto(merchant_cfg.web_url + "/login")
    page.fill("#username", "admin")
    page.fill("#password", "secret")
    page.click("button[type=submit]")
    page.wait_for_url("**/dashboard")
```

### 功能限定测试

```python
@pytest.mark.requires_feature("crypto_payment")
def test_crypto_deposit(api_client):
    # 不支持 crypto_payment 的商户自动跳过，无需 if 判断
    ...
```

---

## FAQ

**Q: 第一次跑需要什么顺序？**
1. 配置商户 YAML → 2. 设置账号密码环境变量 → 3. 跑 UI 录制 → 4. 生成 YAML case → 5. （可选）手动调整 YAML → 6. 生成脚本 → 7. 跑 API 测试

**Q: 只想跑 API 测试，不需要录制 UI？**
直接跑 `pytest tests/api/generated/ --merchant=xxx --env=yyy`，前提是 YAML case 和生成脚本已存在。

**Q: 同一个接口在不同商户有不同的字段怎么办？**
YAML 是按商户分开生成的（文件名可加 `--prefix m1_stg`），不同商户的 YAML 互不干扰。

**Q: 如何给已有的 YAML 增加自定义用例？**
在 YAML 的 `cases` 列表里手动追加，重新跑 `generate_api_tests.py` 即可。

**Q: 边界用例里期望 400 但接口实际返回 200（因为字段是可选的）？**
手动编辑 YAML，把对应 case 的 `expect.status` 改为 `200`，这是 Faker 无法自动判断的，需要人工核查。

**Q: 如何添加新字段的 Faker 映射？**
在 `core/case_generator.py` 顶部的 `_FAKER_FIELD_MAP` 字典里追加：
```python
"member_name": "name",
"contact_phone": "phone_number",
```
