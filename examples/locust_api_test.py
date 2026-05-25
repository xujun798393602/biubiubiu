"""
API 接口性能测试脚本
测试常见 CRUD 操作的性能
"""

from locust import HttpUser, task, between, tag
import json
import random
import string


class ApiCrudUser(HttpUser):
    """API CRUD 操作测试用户"""

    wait_time = between(0.5, 2)

    def on_start(self):
        """初始化：生成测试数据"""
        self.test_ids = []
        self.headers = {
            "Content-Type": "application/json",
            # 如果需要认证，取消下面的注释并填入 token
            # "Authorization": "Bearer YOUR_TOKEN"
        }

    def _random_string(self, length=10):
        """生成随机字符串"""
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

    @tag('read')
    @task(10)
    def list_items(self):
        """查询列表 - 高频操作"""
        params = {
            "page": random.randint(1, 5),
            "pageSize": random.choice([10, 20, 50])
        }
        with self.client.get(
            "/api/v1/cases",
            params=params,
            headers=self.headers,
            name="查询用例列表",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"查询失败: {response.status_code}")

    @tag('read')
    @task(5)
    def get_item_detail(self):
        """获取详情 - 中频操作"""
        item_id = random.choice(self.test_ids) if self.test_ids else "test-id"
        with self.client.get(
            f"/api/v1/cases/{item_id}",
            headers=self.headers,
            name="查询用例详情",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404, 401]:
                response.success()
            else:
                response.failure(f"查询详情失败: {response.status_code}")

    @tag('write')
    @task(2)
    def create_item(self):
        """创建项目 - 低频操作"""
        data = {
            "name": f"性能测试_{self._random_string(6)}",
            "type": "API",
            "api_url": f"http://example.com/api/{self._random_string(5)}",
            "api_method": "GET"
        }
        with self.client.post(
            "/api/v1/cases",
            json=data,
            headers=self.headers,
            name="创建用例",
            catch_response=True
        ) as response:
            if response.status_code in [201, 401]:
                if response.status_code == 201:
                    try:
                        result = response.json()
                        item_id = result.get("data", {}).get("id")
                        if item_id:
                            self.test_ids.append(item_id)
                            # 只保留最近创建的10个ID
                            if len(self.test_ids) > 10:
                                self.test_ids.pop(0)
                    except:
                        pass
                response.success()
            else:
                response.failure(f"创建失败: {response.status_code}")

    @tag('read')
    @task(8)
    def search_items(self):
        """搜索操作 - 高频"""
        keywords = ["测试", "API", "性能", "自动化", "回归"]
        params = {
            "keyword": random.choice(keywords),
            "page": 1,
            "pageSize": 20
        }
        with self.client.get(
            "/api/v1/cases",
            params=params,
            headers=self.headers,
            name="搜索用例",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"搜索失败: {response.status_code}")

    @tag('read')
    @task(3)
    def check_system_status(self):
        """检查系统状态"""
        with self.client.get(
            "/api/v1/nodes/stats",
            headers=self.headers,
            name="系统状态",
            catch_response=True
        ) as response:
            if response.status_code in [200, 401]:
                response.success()
            else:
                response.failure(f"状态检查失败: {response.status_code}")


class ConcurrentTaskUser(HttpUser):
    """并发任务执行测试"""

    wait_time = between(1, 3)

    @tag('task')
    @task
    def execute_task_flow(self):
        """模拟完整任务执行流程"""
        # 1. 获取任务列表
        self.client.get("/api/v1/tasks", name="任务列表")

        # 2. 获取节点列表
        self.client.get("/api/v1/nodes", name="节点列表")

        # 3. 获取统计信息
        self.client.get("/api/v1/nodes/stats", name="节点统计")
