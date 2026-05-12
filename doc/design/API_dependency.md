# 自动化测试平台 — API 接口依赖关系文档

**文档版本：** V1.0
**创建日期：** 2026-05-12

---

## 1. 概述

本文档描述各 API 接口之间的调用依赖关系和参数映射关系，用于指导前后端联调和后端实现。

---

## 2. 跨 API 调用顺序依赖

### 2.1 认证流程依赖链

```
POST /auth/login          ──► 获取 token
        │
        ├──► GET /auth/me             (需要 token)
        ├──► POST /auth/refresh-token (需要 token)
        └──► POST /auth/logout        (需要 token)

POST /auth/forgot-password ──► POST /auth/verify-code ──► POST /auth/reset-password
     (发送验证码)                (验证验证码,返回reset_token)  (使用reset_token重置密码)
```

**依赖说明：**
- 所有需要认证的 API 必须先调用 `/auth/login` 获取 token
- `/auth/verify-code` 依赖 `/auth/forgot-password` 先发送验证码
- `/auth/reset-password` 依赖 `/auth/verify-code` 返回的 `reset_token`

### 2.2 用例管理依赖链

```
POST /cases               ──► 创建用例，返回 case_id
        │
        ├──► GET /cases/{id}/versions  (需要 case_id)
        ├──► PUT /cases/{id}           (需要 case_id)
        ├──► DELETE /cases/{id}        (需要 case_id)
        └──► POST /cases/{id}/rollback (需要 case_id + version)

POST /cases/import         ──► 批量创建用例
POST /cases/export         ──► 依赖已存在的用例数据
```

### 2.3 任务管理依赖链

```
POST /tasks                ──► 创建任务，需要 case_ids[]（来自用例管理）
        │
        ├──► POST /tasks/{id}/start   (PENDING → RUNNING)
        │           │
        │           └──► 系统内部：调度器分配到节点执行
        │                     │
        │                     ├──► POST /nodes/{id}/heartbeat (节点心跳)
        │                     └──► 执行引擎写入 test_results
        │
        ├──► POST /tasks/{id}/cancel  (RUNNING → CANCELLED)
        ├──► GET /tasks/{id}          (查看任务详情)
        ├──► GET /tasks/{id}/logs     (查看执行日志)
        └──► DELETE /tasks/{id}       (软删除)
```

**依赖说明：**
- 创建任务时必须提供至少一个有效的 `case_ids`
- 任务启动依赖节点可用（`test_nodes` 表有 ONLINE 状态的节点）
- 任务执行结果通过执行引擎异步写入 `test_results` 表

### 2.4 结果查看依赖链

```
GET /results/overview      ──► 依赖 task_id（任务完成后才有数据）
GET /results               ──► 依赖 task_id
GET /results/api/{id}      ──► 依赖 result_id
        │
        ├──► POST /results/{task_id}/export  (导出报告)
        └──► POST /results/{task_id}/share   (生成分享链接)
                    │
                    └──► GET /results/share/{token}  (公开访问，无需认证)
```

### 2.5 节点管理依赖链

```
POST /nodes/groups         ──► 创建分组，返回 group_id
POST /nodes                ──► 注册节点，可关联 group_id
        │
        ├──► POST /nodes/{id}/heartbeat  (客户端定期上报)
        ├──► PUT /nodes/{id}             (更新/禁用/启用)
        └──► DELETE /nodes/{id}          (删除节点)
```

### 2.6 系统管理依赖链

```
GET /system/logs           ──► 系统自动记录，无前置依赖
GET /system/notifications  ──► 系统自动生成（任务完成/节点离线等触发）
PUT /system/notifications/{id}/read ──► 依赖 notification_id
GET /system/config         ──► 无前置依赖
PUT /system/config         ──► 依赖 ADMIN 权限
```

---

## 3. API 参数到数据模型字段映射

### 3.1 认证模块（AUTH）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| POST /auth/login | username | users.username | |
| POST /auth/login | password | 与 users.password_hash 比对 | bcrypt 验证 |
| POST /auth/login | - | users.login_fail_count | 失败时递增 |
| POST /auth/login | - | users.locked_until | 达到上限时设置 |
| POST /auth/login | - | users.is_active | 检查账号是否启用 |
| GET /auth/me | - | users.id, username, email | 返回用户信息 |
| GET /auth/me | - | roles.code, permissions | 通过 user_roles 关联 |
| POST /auth/forgot-password | email | users.email | 查找用户 |
| POST /auth/reset-password | new_password | users.password_hash | bcrypt 加密存储 |

### 3.2 用例管理模块（CASE）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| GET /cases | type | test_cases.type | 筛选条件 |
| GET /cases | status | test_cases.status | 筛选条件 |
| GET /cases | priority | test_cases.priority | 筛选条件 |
| GET /cases | keyword | test_cases.name | LIKE 模糊匹配 |
| POST /cases | name | test_cases.name | |
| POST /cases | type | test_cases.type | UI/API/PERFORMANCE |
| POST /cases | ui_script | test_cases.ui_script | UI用例脚本 |
| POST /cases | api_url | test_cases.api_url | 接口用例URL |
| POST /cases | api_method | test_cases.api_method | |
| POST /cases | perf_vusers | test_cases.perf_vusers | 性能用例并发数 |
| POST /cases | - | test_cases.version | 初始值1 |
| POST /cases | - | test_cases.creator_id | 从token解析 |
| PUT /cases/{id} | (部分字段) | test_cases.(对应字段) | version 自动递增 |
| POST /cases/{id}/rollback | version | test_cases.version | 恢复历史版本内容 |

### 3.3 任务管理模块（TASK）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| POST /tasks | name | tasks.name | |
| POST /tasks | priority | tasks.priority | |
| POST /tasks | case_ids[] | task_cases.case_id | 写入关联表 |
| POST /tasks | execute_type | tasks.execute_type | IMMEDIATE/SCHEDULED |
| POST /tasks | schedule_cron | tasks.schedule_cron | 定时表达式 |
| POST /tasks | node_id | tasks.node_id | 指定节点 |
| POST /tasks | - | tasks.total_cases | = len(case_ids) |
| POST /tasks | - | tasks.creator_id | 从token解析 |
| POST /tasks/{id}/start | - | tasks.status | PENDING → RUNNING |
| POST /tasks/{id}/start | - | tasks.started_at | 设置开始时间 |
| POST /tasks/{id}/cancel | - | tasks.status | → CANCELLED |
| POST /tasks/{id}/cancel | - | tasks.completed_at | 设置完成时间 |
| GET /tasks/{id}/logs | level | task_logs.level | 筛选条件 |

### 3.4 结果模块（RESULT）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| GET /results/overview | task_id | test_results.task_id | 聚合查询 |
| GET /results/overview | - | test_results.status | 统计各状态数量 |
| GET /results | task_id | test_results.task_id | 筛选条件 |
| GET /results | status | test_results.status | 筛选条件 |
| GET /results/api/{id} | - | test_results.* | 完整结果数据 |
| GET /results/api/{id} | - | test_results.detail | JSONB 详细信息 |
| POST /results/{task_id}/share | expires_in | result_shares.expires_at | 计算过期时间 |
| POST /results/{task_id}/share | password | result_shares.password_hash | bcrypt 加密 |
| POST /results/{task_id}/share | - | result_shares.token | 系统生成 |
| GET /results/share/{token} | token | result_shares.token | 查找分享记录 |
| GET /results/share/{token} | password | result_shares.password_hash | 密码验证 |

### 3.5 节点管理模块（NODE）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| POST /nodes | name | test_nodes.name | |
| POST /nodes | host | test_nodes.host | |
| POST /nodes | port | test_nodes.port | |
| POST /nodes | group_id | test_nodes.group_id | 关联分组 |
| POST /nodes | max_concurrent | test_nodes.max_concurrent | |
| POST /nodes | - | test_nodes.status | 初始 OFFLINE |
| POST /nodes/{id}/heartbeat | cpu_usage | test_nodes.cpu_usage | 更新指标 |
| POST /nodes/{id}/heartbeat | memory_usage | test_nodes.memory_usage | |
| POST /nodes/{id}/heartbeat | disk_usage | test_nodes.disk_usage | |
| POST /nodes/{id}/heartbeat | current_tasks | test_nodes.current_tasks | |
| POST /nodes/{id}/heartbeat | - | test_nodes.last_heartbeat_at | 更新心跳时间 |
| PUT /nodes/{id} | is_enabled | test_nodes.is_enabled | 禁用/启用 |

### 3.6 系统管理模块（SYS）

| API | 请求参数 | 数据模型字段 | 说明 |
|-----|---------|------------|------|
| GET /system/logs | operation | system_logs.operation | 筛选条件 |
| GET /system/logs | resource_type | system_logs.resource_type | 筛选条件 |
| PUT /system/notifications/{id}/read | - | notifications.is_read | 设置为true |
| PUT /system/notifications/{id}/read | - | notifications.read_at | 设置当前时间 |
| GET /system/config | - | system_configs.key, value | 返回全部配置 |
| PUT /system/config | configs[].key | system_configs.key | |
| PUT /system/config | configs[].value | system_configs.value | |

---

## 4. 异步依赖关系

### 4.1 任务执行异步流

```
POST /tasks/{id}/start (同步)
        │
        ▼
   ┌─────────────┐
   │  调度器队列   │  (Redis Queue)
   └──────┬──────┘
          │ 异步
          ▼
   ┌─────────────┐     POST /nodes/{id}/heartbeat
   │  节点执行    │◄──────────────────────────────────
   └──────┬──────┘
          │ 异步写入
          ▼
   ┌─────────────┐
   │ test_results │  (执行结果)
   └──────┬──────┘
          │ 异步触发
          ▼
   ┌─────────────┐
   │notifications │  (任务完成通知)
   └─────────────┘
```

### 4.2 节点状态异步更新

```
节点客户端 ──(每30秒)──► POST /nodes/{id}/heartbeat
                              │
                              ▼
                    更新 test_nodes 指标
                              │
                              ▼
                    检查节点离线状态 (90秒超时)
                              │
                              ▼
                    触发 notifications (NODE_OFFLINE)
```

---

## 5. 缓存依赖关系

| 缓存Key | 数据来源 | 依赖API | TTL |
|---------|---------|---------|-----|
| token:blacklist:{hash} | POST /auth/logout | /auth/login (获取token) | Token剩余有效期 |
| captcha:{email} | POST /auth/forgot-password | - | 300秒 |
| lock:user:{id} | POST /auth/login (失败时) | - | 3600秒 |
| cache:config:{key} | GET /system/config | PUT /system/config (更新时清除) | 300秒 |
| node:heartbeat:{id} | POST /nodes/{id}/heartbeat | - | 90秒 |
