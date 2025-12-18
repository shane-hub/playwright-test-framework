# 更新日志

## [2025-12-18] - 测试报告时间戳命名

### 新增功能
- ✨ 测试报告现在使用时间戳命名格式：`YYYYMMDD_HHMMSS_UI.html` 和 `YYYYMMDD_HHMMSS_API.html`
- 📊 每次运行测试都会生成新的报告文件,不会覆盖之前的报告
- 🔍 方便追踪和对比不同时间点的测试结果

### 修改内容
- 修改 `run_tests.py`:
  - 导入 `datetime` 模块
  - 在 `SmartTestRunner` 类中添加 `ui_report_name` 和 `api_report_name` 属性
  - 在 `run_ui_tests()` 方法中生成时间戳格式的 UI 报告文件名
  - 在 `run_api_tests()` 方法中生成时间戳格式的 API 报告文件名
  - 更新测试完成后的报告路径输出

### 示例
运行测试后,报告文件将类似于:
```
reports/
├── api/
│   ├── 20251218_085911_API.html
│   └── 20251218_090000_API.html
└── ui/
    ├── 20251218_090500_UI.html
    └── 20251218_091000_UI.html
```

### 使用方法
```bash
# 运行 API 测试并生成报告
python run_tests.py api

# 运行 UI 测试并生成报告
python run_tests.py ui

# 运行完整流程
python run_tests.py full
```

报告文件名会自动包含运行时的时间戳,无需手动管理。
