"""
基础 Locust 性能测试脚本示例
用于验证 Locust Worker 分布式执行功能
"""

from locust import HttpUser, task, between, events
import json
import time


class BasicApiUser(HttpUser):
    """基础 API 测试用户"""

    # 请求间隔：1-3秒
    wait_time = between(1, 3)

    @task(10)
    def test_home_page(self):
        """测试首页 - 权重10"""
        with self.client.get("/", name="首页", catch_response=True) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"首页请求失败: {response.status_code}")

    @task(5)
    def test_health_check(self):
        """测试健康检查接口 - 权重5"""
        with self.client.get("/api/v1/health", name="健康检查", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "ok":
                        response.success()
                    else:
                        response.failure(f"健康检查状态异常: {data}")
                except json.JSONDecodeError:
                    response.failure("响应不是有效的 JSON")
            else:
                response.failure(f"健康检查失败: {response.status_code}")

    @task(3)
    def test_api_list(self):
        """测试 API 列表接口 - 权重3"""
        with self.client.get("/api/v1/cases?page=1&pageSize=10", name="用例列表", catch_response=True) as response:
            if response.status_code in [200, 401]:  # 401 表示需要认证，接口存在
                response.success()
            else:
                response.failure(f"用例列表请求失败: {response.status_code}")

    @task(2)
    def test_slow_request(self):
        """模拟慢请求 - 权重2"""
        with self.client.get("/api/v1/nodes", name="节点列表", catch_response=True) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"节点列表请求失败: {response.status_code}")

    def on_start(self):
        """用户启动时执行"""
        print(f"用户 {self.environment.runner.user_count if self.environment.runner else 'N/A'} 开始测试")

    def on_stop(self):
        """用户停止时执行"""
        print("用户停止测试")


class StressTestUser(HttpUser):
    """压力测试用户 - 模拟高并发"""

    wait_time = between(0.1, 0.5)  # 更短的等待时间

    @task
    def rapid_requests(self):
        """快速连续请求"""
        self.client.get("/", name="快速请求")


# 事件监听器
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """请求完成时的回调"""
    if exception:
        print(f"请求失败: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """测试开始时的回调"""
    print("=" * 50)
    print("性能测试开始")
    print(f"目标主机: {environment.host}")
    print("=" * 50)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """测试结束时的回调"""
    print("=" * 50)
    print("性能测试结束")
    print("=" * 50)
