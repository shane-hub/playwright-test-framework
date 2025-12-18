"""
API 测试用例 - 自动生成
生成时间: 2025-12-17 21:54:04
请求数量: 2
"""
import pytest

def test_get_test_1(api_client):
    """
    测试: GET https://jsonplaceholder.typicode.com/users/1
    自动生成于: 2025-12-17 21:54:04
    """
    data = None
    headers = {
        "Content-Type": "application/json"
}
    
    # 发送请求
    response = api_client.send_request(
        method="GET",
        url="https://jsonplaceholder.typicode.com/users/1",
        json=data,
        headers=headers
    )
    
    # 断言
    api_client.assert_status_code(response, 200)
    api_client.assert_response_time(response, max_time=3000)
    assert response.json() is not None

def test_post_posts(api_client):
    """
    测试: POST https://jsonplaceholder.typicode.com/posts
    自动生成于: 2025-12-17 21:54:04
    """
    data = {
        "title": "Test Post",
        "body": "Content",
        "userId": 1
}
    headers = {
        "Content-Type": "application/json"
}
    
    # 发送请求
    response = api_client.send_request(
        method="POST",
        url="https://jsonplaceholder.typicode.com/posts",
        json=data,
        headers=headers
    )
    
    # 断言
    api_client.assert_status_code(response, 201)
    api_client.assert_response_time(response, max_time=3000)
    assert response.json() is not None