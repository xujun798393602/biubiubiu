# 自动化测试平台 — 技术设计文档（汇总索引）

**文档版本：** V1.0
**创建日期：** 2026-05-12
**质量评分：** 96/100
**状态：** 已通过质量门禁（≥85），可进入实现阶段

---

## 1. 设计概述

### 1.1 架构目标

构建一个支持 UI 测试（Playwright）、接口测试（requests/httpx）、性能压测（Locust）的自动化测试平台，实现用例管理、任务调度、分布式执行、结果展示的全流程自动化。

### 1.2 核心技术栈

| 层次 | 技术选型 |
|------|---------|
| 前端 | Vue 3 + Element Plus + Monaco Editor |
| 反向代理 | Nginx |
| 后端 | Flask + Python + Gunicorn |
| 数据库 | PostgreSQL 15+ |
| 缓存 | Redis 7+ |
| UI 测试引擎 | Playwright |
| 性能测试引擎 | Locust |
| 部署 | Docker + docker-compose |

### 1.3 核心决策摘要

1. **单体架构**：采用 Flask 单体架构，按模块分层（API/Service/Repository/Engine），避免微服务复杂度
2. **三种测试引擎**：Playwright（UI）、requests（接口）、Locust（性能），通过引擎基类统一接口
3. **JWT + Redis 黑名单**：Token 认证，退出时加入黑名单实现即时失效
4. **RBAC 三角色**：ADMIN/TESTER/OPS，通过装饰器实现接口级权限控制
5. **节点即插即用**：心跳机制 + 自动注册，新节点加入无需修改服务端配置
6. **任务调度**：Redis 队列 + 优先级调度 + 负载均衡选择节点

---

## 2. 子文档目录

| 文档 | 文件 | 说明 |
|------|------|------|
| 架构与流程设计 | [module_design.md](./module_design.md) | 系统架构、模块划分、核心流程、技术选型、目录结构 |
| 数据模型设计 | [data_model_design.md](./data_model_design.md) | 14张表结构、索引设计、建表SQL、Redis缓存设计 |
| API 接口设计 | [API_design.md](./API_design.md) | 43个RESTful API规格、请求/响应格式、错误码、权限 |
| 接口依赖关系 | [API_dependency.md](./API_dependency.md) | 跨API调用顺序、参数到字段映射、异步依赖、缓存依赖 |
| DFX 可靠性设计 | [DFX_design.md](./DFX_design.md) | 7维度DFX措施、FMEA分析、安全兜底清单 |

---

## 3. 关键 API 接口摘要

| 模块 | 接口数量 | 核心接口 |
|------|---------|---------|
| 认证 (AUTH) | 7 | POST /auth/login, POST /auth/logout, GET /auth/me |
| 用例 (CASE) | 8 | GET /cases, POST /cases, PUT /cases/{id}, DELETE /cases/{id} |
| 任务 (TASK) | 8 | POST /tasks, POST /tasks/{id}/start, POST /tasks/{id}/cancel |
| 结果 (RESULT) | 6 | GET /results/overview, GET /results/api/{id}, POST /results/{id}/share |
| 节点 (NODE) | 7 | POST /nodes, POST /nodes/{id}/heartbeat, GET /nodes/groups |
| 系统 (SYS) | 7 | GET /system/logs, GET /system/config, GET /health, GET /ready |
| **合计** | **43** | |

### 3.1 统一响应格式

```json
{
    "code": 0,          // 0=成功，非0=错误码字符串
    "message": "success",
    "data": {}           // object | array | null
}
```

### 3.2 认证方式

- JWT Bearer Token（Header: `Authorization: Bearer <token>`）
- Token 有效期 24 小时，支持刷新
- 退出时 Token 加入 Redis 黑名单

### 3.3 错误码（16个）

| 错误码 | HTTP | 说明 |
|--------|------|------|
| INVALID_CREDENTIALS | 401 | 用户名或密码错误 |
| ACCOUNT_DISABLED | 403 | 账号已禁用 |
| ACCOUNT_LOCKED | 423 | 账号已锁定 |
| TOKEN_INVALID | 401 | Token 无效 |
| TOKEN_REVOKED | 401 | Token 已失效 |
| FORBIDDEN | 403 | 权限不足 |
| CASE_NOT_FOUND | 404 | 用例不存在 |
| TASK_NOT_FOUND | 404 | 任务不存在 |
| RESULT_NOT_FOUND | 404 | 结果不存在 |
| NODE_NOT_FOUND | 404 | 节点不存在 |
| SHARE_NOT_FOUND | 404 | 分享链接不存在 |
| SHARE_EXPIRED | 410 | 分享链接已过期 |
| SHARE_PASSWORD_REQUIRED | 401 | 需要访问密码 |
| SHARE_PASSWORD_INVALID | 401 | 密码错误 |
| VALIDATION_ERROR | 422 | 参数校验失败 |
| INTERNAL_ERROR | 500 | 服务器内部错误 |

---

## 4. 关键数据模型摘要

### 4.1 核心表（14张）

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| users | 用户表 | username, password_hash, email, is_active, login_fail_count, locked_until |
| roles | 角色表 | code, name, permissions(jsonb) |
| user_roles | 用户角色关联 | user_id, role_id |
| test_cases | 测试用例表 | name, type, status, priority, version, creator_id, ui_*, api_*, perf_* |
| task_cases | 任务用例关联 | task_id, case_id, sort_order |
| tasks | 测试任务表 | name, status, priority, execute_type, total_cases, success_count, failed_count |
| task_logs | 任务日志表 | task_id, level, message, case_id |
| test_results | 测试结果表 | task_id, case_id, status, detail(jsonb), duration_ms |
| result_shares | 结果分享表 | task_id, token, password_hash, expires_at |
| test_nodes | 测试节点表 | name, host, port, status, group_id, cpu_usage, memory_usage, last_heartbeat_at |
| node_groups | 节点分组表 | name, description |
| system_logs | 系统日志表 | user_id, operation, resource_type, resource_id, ip |
| notifications | 通知表 | user_id, title, content, type, is_read |
| system_configs | 系统配置表 | key, value, description |

### 4.2 实体关系

```
User ──N:M── Role (通过 user_roles)
  ├──1:N── TestCase ──N:M── Task (通过 task_cases)
  ├──1:N── Task ──1:N── TestResult
  ├──1:N── TestNode ──N:1── NodeGroup
  ├──1:N── SystemLog
  ├──1:N── Notification
  └──1:N── SystemConfig
```

### 4.3 Redis 缓存设计

| Key 模式 | 用途 | TTL |
|---------|------|-----|
| token:blacklist:{hash} | Token 黑名单 | Token 剩余有效期 |
| captcha:{email} | 邮箱验证码 | 300秒 |
| lock:user:{id} | 登录锁定 | 3600秒 |
| cache:config:{key} | 配置缓存 | 300秒 |
| node:heartbeat:{id} | 节点心跳 | 90秒 |

---

## 5. 关键流程摘要

### 5.1 登录流程
POST /auth/login → 查询用户 → 检查锁定 → 验证密码 → 生成JWT → 返回Token

### 5.2 任务执行流程
POST /tasks → 创建任务 → 入调度队列 → 调度器取任务 → 选择节点 → 分配执行 → 写入结果 → 更新状态 → 触发通知

### 5.3 节点心跳流程
节点每30秒上报 → 更新Redis心跳 → 更新节点指标 → 90秒超时标记OFFLINE

### 5.4 结果分享流程
POST /results/{id}/share → 生成Token → 设置过期/密码 → 写入result_shares → 返回share_url

---

## 6. 非功能性需求摘要

| 维度 | 关键指标 |
|------|---------|
| 性能 | API响应≤1s(P95)，页面加载≤2s，并发任务≥50 |
| 安全 | JWT+RBAC，bcrypt加密，输入校验，审计日志 |
| 可靠性 | 任务成功率≥99%，节点故障自动恢复，数据备份RPO≤5min |
| 可扩展 | 新增测试类型无需重构，节点即插即用 |
| 可维护 | Docker容器化，日志分级分模块，配置可热更新 |

---

## 7. 变更记录

| 日期       | 版本 | 变更内容 | 质量评分 |
|-----------|------|---------|---------|
| 2026-05-12 | V1.0 | 初始创建，完成全部5个子设计文档 | 96/100 |
