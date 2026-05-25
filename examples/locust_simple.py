"""
简单 Locust 测试脚本 - 可直接复制到平台使用
用于快速验证分布式性能测试功能
"""

from locust import HttpUser, task, between


class QuickTestUser(HttpUser):
    """快速测试用户"""

    # 每个请求间隔 1-2 秒
    wait_time = between(1, 2)

    @task
    def test_request(self):
        """发送测试请求"""
        self.client.get("/")
