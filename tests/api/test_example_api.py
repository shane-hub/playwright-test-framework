"""
API 测试示例
演示如何使用 API 测试基类
"""
import pytest


@pytest.mark.api
class TestExampleAPI:
    """示例 API 测试类"""
    
    def test_get_request(self, api_client):
        """测试 GET 请求"""
        # 发送 GET 请求
        response = api_client.get("https://jsonplaceholder.typicode.com/posts/1")
        
        # 断言状态码
        api_client.assert_status_code(response, 200)
        
        # 断言响应时间
        api_client.assert_response_time(response, 3000)
        
        # 断言响应包含特定字段
        json_data = response.json()
        assert "userId" in json_data
        assert "id" in json_data
        assert "title" in json_data
    
    def test_post_request(self, api_client):
        """测试 POST 请求"""
        # 准备请求数据
        data = {
            "title": "Test Post",
            "body": "This is a test post",
            "userId": 1
        }
        
        # 发送 POST 请求
        response = api_client.post(
            "https://jsonplaceholder.typicode.com/posts",
            json=data
        )
        
        # 断言状态码
        api_client.assert_status_code(response, 201)
        
        # 断言响应包含提交的数据
        api_client.assert_json_contains(response, {"title": "Test Post"})
    
    def test_with_headers(self, api_client):
        """测试带自定义 headers 的请求"""
        headers = {
            "Custom-Header": "test-value"
        }
        
        response = api_client.get(
            "https://jsonplaceholder.typicode.com/posts/1",
            headers=headers
        )
        
        api_client.assert_status_code(response, 200)
    
    @pytest.mark.parametrize("post_id", [1, 2, 3])
    def test_parametrized(self, api_client, post_id):
        """参数化测试示例"""
        response = api_client.get(
            f"https://jsonplaceholder.typicode.com/posts/{post_id}"
        )
        
        api_client.assert_status_code(response, 200)
        
        json_data = response.json()
        assert json_data["id"] == post_id
    
    def test_error_handling(self, api_client):
        """测试错误处理"""
        # 请求不存在的资源
        response = api_client.get(
            "https://jsonplaceholder.typicode.com/posts/99999"
        )
        
        # 某些 API 可能返回 404,某些返回空对象
        # 这里只是示例
        assert response.status_code in [200, 404]
