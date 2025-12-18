# 智能测试运行器使用指南

## 🎯 核心功能

智能测试运行器实现了完整的自动化测试流程:

1. **运行 UI 测试** - 自动拦截 API 请求
2. **检测 API 变化** - 智能识别新增和变化的 API
3. **自动生成测试** - 有变化时自动重新生成 API 测试用例
4. **运行 API 测试** - 执行最新的 API 测试

## 🚀 快速使用

### 完整流程(推荐)

```bash
# 运行完整的智能测试流程
python run_tests.py full

# 带报告
python run_tests.py full --headless

# 并行运行
python run_tests.py full --parallel 4
```

### 单独运行

```bash
# 只运行 UI 测试
python run_tests.py ui

# 只运行 API 测试
python run_tests.py api

# 无头模式
python run_tests.py ui --headless
```

### 清空缓存

```bash
# 清空 API 缓存,强制重新生成所有测试
python run_tests.py full --clear-cache
```

## 📋 命令参数

```bash
python run_tests.py <mode> [options]

模式:
  ui          只运行 UI 测试
  api         只运行 API 测试
  full        完整流程(UI -> 检测变化 -> 生成测试 -> API)

选项:
  --headless          无头模式运行浏览器
  -p N, --parallel N  并行运行(N个进程)
  --no-report         不生成 HTML 报告
  --clear-cache       清空 API 缓存
```

## 🔄 工作流程详解

### 完整流程 (full)

```
┌─────────────────────────────────────────────────────────┐
│ 步骤 1: 运行 UI 测试                                     │
│ - 执行所有 UI 测试用例                                   │
│ - 自动拦截配置的 API 请求                                │
│ - 保存请求数据到 data/requests/                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤 2: 检测 API 变化                                    │
│ - 读取最新的请求文件                                     │
│ - 与缓存对比,检测新增和变化的 API                        │
│ - 生成变化摘要                                           │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤 3: 重新生成 API 测试 (如果有变化)                   │
│ - 从拦截的请求自动生成测试代码                           │
│ - 保存到 tests/api/generated/                            │
│ - 更新 API 缓存                                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ 步骤 4: 运行 API 测试                                    │
│ - 执行所有 API 测试(包括新生成的)                        │
│ - 生成测试报告                                           │
└─────────────────────────────────────────────────────────┘
```

## 💡 使用场景

### 场景 1: 日常开发

```bash
# 开发过程中,运行完整流程
python run_tests.py full

# 自动检测 API 变化并更新测试
```

### 场景 2: 只测试 UI

```bash
# 只关注 UI 功能
python run_tests.py ui --headless
```

### 场景 3: 只测试 API

```bash
# 快速验证 API
python run_tests.py api
```

### 场景 4: CI/CD 集成

```bash
# 在 CI 中运行
python run_tests.py full --headless --parallel 4 --no-report
```

### 场景 5: 强制重新生成

```bash
# 清空缓存,重新生成所有 API 测试
python run_tests.py full --clear-cache
```

## 🔍 API 变化检测机制

### 检测逻辑

1. **API 签名**: `方法:路径` (例如: `GET:/api/users`)
2. **变化哈希**: 基于方法、URL、请求体结构、响应状态码

### 触发重新生成的条件

- ✅ 新增的 API 端点
- ✅ API 请求体结构变化
- ✅ API 响应状态码变化
- ❌ 仅查询参数变化(不触发)
- ❌ 响应内容变化(不触发)

### 缓存文件

- 位置: `data/.api_cache.json`
- 格式: `{"API签名": "哈希值"}`
- 清空: `--clear-cache` 参数

## 📊 输出示例

### 完整流程输出

```
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀
开始智能测试流程
🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀🚀

============================================================
步骤 1: 运行 UI 测试
============================================================
运行命令: pytest -v -m ui tests/ui/ --html=reports/ui/report.html
✅ UI 测试完成

============================================================
步骤 2: 检测 API 变化
============================================================
📁 最新请求文件: requests_20231217_120000.json
📊 拦截的请求总数: 15

🆕 新增 API: 2 个
   - GET:/api/users/profile
   - POST:/api/orders

🔄 变化的 API: 1 个
   - PUT:/api/users/settings

============================================================
步骤 3: 重新生成 API 测试用例
============================================================
✅ 测试用例已生成: tests/api/generated/test_auto_generated.py

============================================================
步骤 4: 运行 API 测试
============================================================
运行命令: pytest -v -m api tests/api/ --html=reports/api/report.html
✅ API 测试完成

============================================================
测试流程完成
============================================================
UI 测试: ✅ 通过
API 测试: ✅ 通过
API 变化: 🆕 2 个新增, 🔄 1 个变化

📊 测试报告:
  UI: reports/ui/report.html
  API: reports/api/report.html
```

## 🛠️ 高级配置

### 配置拦截的 API

编辑 `config/config.yaml`:

```yaml
interception:
  enabled: true
  hosts:
    - api.yourapp.com
    - backend.yourapp.com
  deduplicate: true
```

### 自定义生成的测试

生成的测试位于 `tests/api/generated/test_auto_generated.py`,你可以:

1. 直接编辑添加更多断言
2. 复制到其他目录作为模板
3. 添加参数化

## 📝 最佳实践

1. **定期清空缓存**: 重大版本更新时使用 `--clear-cache`
2. **CI 集成**: 使用 `--headless --parallel 4`
3. **本地开发**: 使用 `full` 模式获得完整反馈
4. **快速验证**: 使用 `ui` 或 `api` 单独测试
5. **查看报告**: 测试完成后检查 HTML 报告

## ❓ 常见问题

### Q: 为什么没有检测到 API 变化?

A: 检查以下几点:
- UI 测试是否成功运行?
- `data/requests/` 目录是否有新文件?
- 配置文件中 `interception.enabled` 是否为 `true`?
- `interception.hosts` 是否包含你的 API host?

### Q: 如何强制重新生成所有测试?

A: 使用 `--clear-cache` 参数:
```bash
python run_tests.py full --clear-cache
```

### Q: 生成的测试在哪里?

A: `tests/api/generated/test_auto_generated.py`

### Q: 可以手动编辑生成的测试吗?

A: 可以,但建议复制到其他目录,否则下次生成会覆盖。

## 🔗 相关文档

- [README.md](README.md) - 项目总览
- [QUICKSTART.md](QUICKSTART.md) - 快速开始
- [USAGE.md](USAGE.md) - 详细使用指南
