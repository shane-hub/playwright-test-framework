"""
UI 测试示例
演示如何使用 UI 测试基类和请求拦截功能
"""
import pytest
from base.ui_test_base import UITestBase


@pytest.mark.ui
class TestExampleUI(UITestBase):
    """示例 UI 测试类"""
    
    def test_navigate_to_page(self):
        """测试页面导航"""
        # 导航到示例页面
        self.navigate("https://example.com")
        
        # 等待页面加载
        self.wait_for_selector("h1")
        
        # 获取标题文本
        title = self.get_text("h1")
        assert "Example Domain" in title
        
        # 截图
        self.take_screenshot("example_page")
    
    def test_with_interception(self):
        """测试带请求拦截的场景"""
        # 导航到会发起 API 请求的页面
        # 注意: 这里使用 example.com 作为示例,实际使用时替换为你的测试页面
        self.navigate("https://example.com")
        
        # 执行一些操作...
        # self.click("button#submit")
        # self.fill("input#username", "test_user")
        
        # 拦截器会自动记录所有匹配的请求
        # 在 teardown_method 中会自动保存
        
        # 获取拦截的请求摘要
        if self.interceptor:
            summary = self.interceptor.get_summary()
            print(f"拦截的请求摘要: {summary}")
    
    def test_form_submission(self):
        """测试表单提交"""
        # 这是一个示例,展示如何测试表单
        # 实际使用时替换为你的测试场景
        
        # 导航到页面
        # self.navigate("https://your-app.com/login")
        
        # 填充表单
        # self.fill("input[name='username']", "test_user")
        # self.fill("input[name='password']", "test_password")
        
        # 点击提交
        # self.click("button[type='submit']")
        
        # 等待跳转
        # self.wait_for_selector(".dashboard")
        
        # 断言
        # assert self.page.url == "https://your-app.com/dashboard"
        
        # 截图
        # self.take_screenshot("after_login")
        
        pass  # 占位符,实际使用时删除
