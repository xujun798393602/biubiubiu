# 自动化测试平台 — 数据模型设计文档

**文档版本：** V1.0
**创建日期：** 2026-05-12
**最后修改日期：** 2026-05-12

---

## 修订历史

| 版本 | 日期       | 修改说明 | 修改人 | 审核人 |
|------|-----------|---------|--------|--------|
| V1.0 | 2026-05-12 | 初始创建 | -      | -      |

---

## 1. 引言

### 1.1 编写目的

本文档定义自动化测试平台的数据库逻辑模型和物理模型，为后端开发提供数据层实现依据。

### 1.2 适用范围

适用于自动化测试平台后端服务，覆盖认证、用例管理、任务管理、测试结果、节点管理、系统管理六个业务模块。

### 1.3 参考文档

| 文档名称         | 版本 | 发布日期   |
|-----------------|------|-----------|
| 系统需求文档      | 1.0  | 2026-05-12 |
| 用户需求文档      | 1.0  | 2026-05-12 |

### 1.4 术语与缩写

| 术语/缩写 | 解释说明 |
|----------|---------|
| UUID     | 通用唯一标识符，用作主键 |
| JSONB    | PostgreSQL 二进制 JSON 类型 |
| RBAC     | 基于角色的访问控制 |
| JWT      | JSON Web Token |

---

## 2. 数据库环境

- **数据库类型：** PostgreSQL
- **版本：** 15+
- **字符集：** UTF-8
- **排序规则：** en_US.UTF-8（默认）
- **缓存：** Redis 7+（用于 Token 黑名单、验证码、会话缓存）

---

## 3. 数据库命名规范

| 对象类型 | 命名格式 | 示例 | 说明 |
|---------|---------|------|------|
| 表名    | snake_case | test_cases | 小写+下划线，复数形式 |
| 字段名  | snake_case | created_at | 小写+下划线 |
| 主键    | pk_表名 | pk_users | |
| 外键    | fk_源表_目标表 | fk_user_roles_users | |
| 索引    | idx_表名_字段名 | idx_users_username | |
| 唯一索引 | uk_表名_字段名 | uk_users_username | |

---

## 4. 逻辑设计

### 4.1 实体关系图（ERD）

```
┌──────────┐     ┌────────────┐     ┌──────────┐
│  users   │────►│ user_roles │◄────│  roles   │
│          │     └────────────┘     │          │
│          │                        │ code     │
│          │                        │ name     │
│          │                        │permissions│
└────┬─────┘                        └──────────┘
     │
     ├──────────────┬──────────────┬──────────────┐
     ▼              ▼              ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│test_cases│  │  tasks   │  │test_nodes│  │system_logs   │
│          │  │          │  │          │  │notifications │
│          │  │          │  │          │  │system_configs│
└────┬─────┘  └────┬─────┘  └──────────┘  └──────────────┘
     │             │
     │    ┌────────┤
     ▼    ▼        ▼
┌────────────┐ ┌──────────────┐
│ task_cases │ │ test_results │
│ (关联表)    │ │              │
└────────────┘ └──────┬───────┘
                      │
                      ▼
               ┌──────────────┐
               │result_shares │
               └──────────────┘
```

### 4.2 数据表清单

| 表名             | 中文描述     | 备注                    |
|-----------------|------------|------------------------|
| users           | 用户表      | 存储用户账号信息          |
| roles           | 角色表      | ADMIN/TESTER/OPS        |
| user_roles      | 用户角色关联 | 多对多关系               |
| test_cases      | 测试用例表   | 支持UI/接口/性能三种类型   |
| task_cases      | 任务用例关联 | 多对多关系               |
| tasks           | 测试任务表   | 任务调度与执行            |
| task_logs       | 任务日志表   | 执行过程日志             |
| test_results    | 测试结果表   | 每个用例的执行结果        |
| result_shares   | 结果分享表   | 分享链接管理             |
| test_nodes      | 测试节点表   | 节点注册与心跳           |
| node_groups     | 节点分组表   | 节点分组管理             |
| system_logs     | 系统日志表   | 操作审计日志             |
| notifications   | 通知表      | 平台内消息通知           |
| system_configs  | 系统配置表   | 平台运行参数             |

### 4.3 详细表结构

#### 4.3.1 users（用户表）

| 字段名           | 数据类型        | 长度 | 允许空 | 键类型 | 默认值           | 字段说明              |
|-----------------|----------------|------|--------|--------|-----------------|----------------------|
| id              | UUID           |      | NO     | PRI    | gen_random_uuid() | 用户ID，主键          |
| username        | VARCHAR        | 64   | NO     | UNI    |                 | 用户名，唯一          |
| password_hash   | VARCHAR        | 256  | NO     |        |                 | bcrypt 加密密码       |
| email           | VARCHAR        | 128  | NO     | UNI    |                 | 邮箱，唯一            |
| is_active       | BOOLEAN        |      | NO     |        | true            | 账号是否启用          |
| login_fail_count| INTEGER        |      | NO     |        | 0               | 连续登录失败次数      |
| locked_until    | TIMESTAMP      |      | YES    |        | NULL            | 锁定截止时间          |
| created_at      | TIMESTAMP      |      | NO     |        | NOW()           | 创建时间              |
| updated_at      | TIMESTAMP      |      | NO     |        | NOW()           | 更新时间              |
| deleted_at      | TIMESTAMP      |      | YES    |        | NULL            | 软删除时间            |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_users_username` (`username`) WHERE deleted_at IS NULL
- 唯一索引：`uk_users_email` (`email`) WHERE deleted_at IS NULL
- 索引：`idx_users_is_active` (`is_active`)

**表备注：** 系统用户基础信息表，密码使用 bcrypt 加密存储。

#### 4.3.2 roles（角色表）

| 字段名       | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明         |
|-------------|-----------|------|--------|--------|-----------------|-----------------|
| id          | UUID      |      | NO     | PRI    | gen_random_uuid() | 角色ID          |
| code        | VARCHAR   | 32   | NO     | UNI    |                 | 角色编码         |
| name        | VARCHAR   | 64   | NO     |        |                 | 角色名称         |
| permissions | JSONB     |      | NO     |        | '{}'            | 权限配置(jsonb)  |
| created_at  | TIMESTAMP |      | NO     |        | NOW()           | 创建时间         |
| updated_at  | TIMESTAMP |      | NO     |        | NOW()           | 更新时间         |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_roles_code` (`code`)

**表备注：** 角色定义表，permissions 存储模块级权限矩阵。

#### 4.3.3 user_roles（用户角色关联表）

| 字段名      | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明    |
|------------|-----------|------|--------|--------|-----------------|-----------|
| id         | UUID      |      | NO     | PRI    | gen_random_uuid() | 主键       |
| user_id    | UUID      |      | NO     | FK     |                 | 用户ID     |
| role_id    | UUID      |      | NO     | FK     |                 | 角色ID     |
| created_at | TIMESTAMP |      | NO     |        | NOW()           | 创建时间    |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_user_roles_user_role` (`user_id`, `role_id`)
- 外键：`fk_user_roles_users` (`user_id`) → `users(id)`
- 外键：`fk_user_roles_roles` (`role_id`) → `roles(id)`

**表备注：** 用户与角色的多对多关联表。

#### 4.3.4 test_cases（测试用例表）

| 字段名             | 数据类型    | 长度 | 允许空 | 键类型 | 默认值           | 字段说明                    |
|-------------------|------------|------|--------|--------|-----------------|----------------------------|
| id                | UUID       |      | NO     | PRI    | gen_random_uuid() | 用例ID                      |
| name              | VARCHAR    | 256  | NO     |        |                 | 用例名称                     |
| type              | VARCHAR    | 32   | NO     |        |                 | 类型：UI/API/PERFORMANCE     |
| status            | VARCHAR    | 32   | NO     |        | 'DRAFT'         | 状态：DRAFT/ACTIVE/DEPRECATED|
| priority          | VARCHAR    | 8    | NO     |        | 'P2'            | 优先级：P0/P1/P2/P3         |
| module            | VARCHAR    | 128  | YES    |        | NULL            | 所属模块                     |
| tags              | JSONB      |      | YES    |        | '[]'            | 标签列表                     |
| description       | TEXT       |      | YES    |        | NULL            | 用例描述                     |
| preconditions     | TEXT       |      | YES    |        | NULL            | 前置条件                     |
| steps             | JSONB      |      | YES    |        | '[]'            | 执行步骤                     |
| expected_result   | TEXT       |      | YES    |        | NULL            | 预期结果                     |
| assertions        | JSONB      |      | YES    |        | '[]'            | 断言规则                     |
| version           | INTEGER    |      | NO     |        | 1               | 版本号                       |
| creator_id        | UUID       |      | NO     | FK     |                 | 创建人ID                     |
| ui_url            | VARCHAR    | 512  | YES    |        | NULL            | UI测试目标URL                |
| ui_script         | TEXT       |      | YES    |        | NULL            | Playwright脚本内容           |
| ui_script_type    | VARCHAR    | 32   | YES    |        | NULL            | RECORDED/MANUAL              |
| ui_screenshots    | JSONB      |      | YES    |        | '[]'            | 关键步骤截图路径              |
| ui_video_path     | VARCHAR    | 512  | YES    |        | NULL            | 执行录像路径                  |
| api_url           | VARCHAR    | 512  | YES    |        | NULL            | 接口地址                     |
| api_method        | VARCHAR    | 16   | YES    |        | NULL            | GET/POST/PUT/DELETE/PATCH    |
| api_headers       | JSONB      |      | YES    |        | NULL            | 请求头                       |
| api_body_type     | VARCHAR    | 16   | YES    |        | NULL            | NONE/JSON/FORM/XML/RAW      |
| api_body          | TEXT       |      | YES    |        | NULL            | 请求体                       |
| api_timeout       | INTEGER    |      | YES    |        | 30000           | 超时时间(ms)                 |
| api_assertions    | JSONB      |      | YES    |        | '[]'            | 接口断言规则                  |
| api_dependencies  | JSONB      |      | YES    |        | '[]'            | 接口依赖配置                  |
| perf_url          | VARCHAR    | 512  | YES    |        | NULL            | 压测目标URL                  |
| perf_vusers       | INTEGER    |      | YES    |        | NULL            | 并发用户数                    |
| perf_spawn_rate   | INTEGER    |      | YES    |        | NULL            | 用户增长率(用户/秒)           |
| perf_duration     | INTEGER    |      | YES    |        | NULL            | 持续时间(秒)                 |
| perf_locustfile   | TEXT       |      | YES    |        | NULL            | Locust脚本内容               |
| perf_assertions   | JSONB      |      | YES    |        | '[]'            | 性能断言规则                  |
| created_at        | TIMESTAMP  |      | NO     |        | NOW()           | 创建时间                     |
| updated_at        | TIMESTAMP  |      | NO     |        | NOW()           | 更新时间                     |
| deleted_at        | TIMESTAMP  |      | YES    |        | NULL            | 软删除时间                   |

**索引设计：**
- 主键：`id`
- 索引：`idx_test_cases_type` (`type`) WHERE deleted_at IS NULL
- 索引：`idx_test_cases_status` (`status`) WHERE deleted_at IS NULL
- 索引：`idx_test_cases_priority` (`priority`) WHERE deleted_at IS NULL
- 索引：`idx_test_cases_creator_id` (`creator_id`)
- 索引：`idx_test_cases_created_at` (`created_at` DESC)
- 全文索引：`idx_test_cases_name_gin` ON `name` USING gin (to_tsvector('simple', name))

**表备注：** 测试用例主表，通过 type 字段区分 UI/接口/性能用例，各类型扩展字段独立存储。

#### 4.3.5 task_cases（任务用例关联表）

| 字段名      | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明    |
|------------|-----------|------|--------|--------|-----------------|-----------|
| id         | UUID      |      | NO     | PRI    | gen_random_uuid() | 主键       |
| task_id    | UUID      |      | NO     | FK     |                 | 任务ID     |
| case_id    | UUID      |      | NO     | FK     |                 | 用例ID     |
| sort_order | INTEGER   |      | NO     |        | 0               | 执行顺序    |
| created_at | TIMESTAMP |      | NO     |        | NOW()           | 创建时间    |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_task_cases_task_case` (`task_id`, `case_id`)
- 外键：`fk_task_cases_tasks` (`task_id`) → `tasks(id)` ON DELETE CASCADE
- 外键：`fk_task_cases_cases` (`case_id`) → `test_cases(id)`
- 索引：`idx_task_cases_case_id` (`case_id`)

**表备注：** 任务与用例的多对多关联表，sort_order 控制执行顺序。

#### 4.3.6 tasks（测试任务表）

| 字段名          | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明                    |
|----------------|-----------|------|--------|--------|-----------------|----------------------------|
| id             | UUID      |      | NO     | PRI    | gen_random_uuid() | 任务ID                      |
| name           | VARCHAR   | 256  | NO     |        |                 | 任务名称                     |
| description    | TEXT      |      | YES    |        | NULL            | 任务描述                     |
| status         | VARCHAR   | 32   | NO     |        | 'PENDING'       | 状态                         |
| priority       | VARCHAR   | 8    | NO     |        | 'P2'            | 优先级：P0/P1/P2/P3         |
| execute_type   | VARCHAR   | 16   | NO     |        | 'IMMEDIATE'     | IMMEDIATE/SCHEDULED          |
| schedule_cron  | VARCHAR   | 64   | YES    |        | NULL            | Cron表达式                   |
| node_id        | UUID      |      | YES    | FK     | NULL            | 指定执行节点                  |
| total_cases    | INTEGER   |      | NO     |        | 0               | 用例总数                     |
| success_count  | INTEGER   |      | NO     |        | 0               | 成功数                       |
| failed_count   | INTEGER   |      | NO     |        | 0               | 失败数                       |
| started_at     | TIMESTAMP |      | YES    |        | NULL            | 开始执行时间                  |
| completed_at   | TIMESTAMP |      | YES    |        | NULL            | 完成时间                     |
| creator_id     | UUID      |      | NO     | FK     |                 | 创建人ID                     |
| created_at     | TIMESTAMP |      | NO     |        | NOW()           | 创建时间                     |
| updated_at     | TIMESTAMP |      | NO     |        | NOW()           | 更新时间                     |
| deleted_at     | TIMESTAMP |      | YES    |        | NULL            | 软删除时间                   |

**状态值：** PENDING, SCHEDULED, RUNNING, SUCCESS, FAILED, CANCELLED

**索引设计：**
- 主键：`id`
- 索引：`idx_tasks_status` (`status`) WHERE deleted_at IS NULL
- 索引：`idx_tasks_priority` (`priority`) WHERE deleted_at IS NULL
- 索引：`idx_tasks_creator_id` (`creator_id`)
- 索引：`idx_tasks_created_at` (`created_at` DESC)
- 索引：`idx_tasks_node_id` (`node_id`)

**表备注：** 测试任务主表，状态机：PENDING→RUNNING→SUCCESS/FAILED，可CANCELLED。

#### 4.3.7 task_logs（任务日志表）

| 字段名      | 数据类型          | 长度 | 允许空 | 键类型 | 默认值           | 字段说明         |
|------------|------------------|------|--------|--------|-----------------|-----------------|
| id         | UUID             |      | NO     | PRI    | gen_random_uuid() | 日志ID          |
| task_id    | UUID             |      | NO     | FK     |                 | 任务ID          |
| level      | VARCHAR          | 16   | NO     |        | 'INFO'          | 日志级别         |
| message    | TEXT             |      | NO     |        |                 | 日志消息         |
| case_id    | UUID             |      | YES    | FK     | NULL            | 关联用例ID       |
| created_at | TIMESTAMP        |      | NO     |        | NOW()           | 创建时间         |

**日志级别值：** DEBUG, INFO, WARNING, ERROR

**索引设计：**
- 主键：`id`
- 索引：`idx_task_logs_task_id` (`task_id`, `created_at` DESC)
- 索引：`idx_task_logs_level` (`level`)

**表备注：** 任务执行过程日志，支持按时间排序查询。

#### 4.3.8 test_results（测试结果表）

| 字段名        | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明                    |
|--------------|-----------|------|--------|--------|-----------------|----------------------------|
| id           | UUID      |      | NO     | PRI    | gen_random_uuid() | 结果ID                      |
| task_id      | UUID      |      | NO     | FK     |                 | 任务ID                      |
| case_id      | UUID      |      | NO     | FK     |                 | 用例ID                      |
| status       | VARCHAR   | 16   | NO     |        |                 | 执行状态                     |
| detail       | JSONB     |      | YES    |        | '{}'            | 详细结果(jsonb)              |
| duration_ms  | INTEGER   |      | YES    |        | NULL            | 执行耗时(ms)                 |
| error_message| TEXT      |      | YES    |        | NULL            | 错误信息                     |
| screenshots  | JSONB     |      | YES    |        | '[]'            | 截图路径列表                  |
| video_path   | VARCHAR   | 512  | YES    |        | NULL            | 录像路径                     |
| started_at   | TIMESTAMP |      | YES    |        | NULL            | 开始时间                     |
| completed_at | TIMESTAMP |      | YES    |        | NULL            | 完成时间                     |
| created_at   | TIMESTAMP |      | NO     |        | NOW()           | 创建时间                     |
| updated_at   | TIMESTAMP |      | NO     |        | NOW()           | 更新时间                     |

**状态值：** SUCCESS, FAILED, SKIPPED, ERROR

**索引设计：**
- 主键：`id`
- 索引：`idx_test_results_task_id` (`task_id`)
- 索引：`idx_test_results_case_id` (`case_id`)
- 索引：`idx_test_results_status` (`status`)
- 唯一索引：`uk_test_results_task_case` (`task_id`, `case_id`)

**表备注：** 每个用例在每次任务执行中的结果记录。

#### 4.3.9 result_shares（结果分享表）

| 字段名         | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明         |
|---------------|-----------|------|--------|--------|-----------------|-----------------|
| id            | UUID      |      | NO     | PRI    | gen_random_uuid() | 分享ID          |
| task_id       | UUID      |      | NO     | FK     |                 | 任务ID          |
| token         | VARCHAR   | 64   | NO     | UNI    |                 | 分享Token       |
| password_hash | VARCHAR   | 256  | YES    |        | NULL            | 访问密码hash     |
| expires_at    | TIMESTAMP |      | YES    |        | NULL            | 过期时间         |
| creator_id    | UUID      |      | NO     | FK     |                 | 创建人ID        |
| created_at    | TIMESTAMP |      | NO     |        | NOW()           | 创建时间         |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_result_shares_token` (`token`)
- 索引：`idx_result_shares_task_id` (`task_id`)
- 索引：`idx_result_shares_expires_at` (`expires_at`)

**表备注：** 结果分享链接管理，token 用于公开访问，支持密码保护和过期时间。

#### 4.3.10 test_nodes（测试节点表）

| 字段名             | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明                |
|-------------------|-----------|------|--------|--------|-----------------|------------------------|
| id                | UUID      |      | NO     | PRI    | gen_random_uuid() | 节点ID                  |
| name              | VARCHAR   | 128  | NO     |        |                 | 节点名称                |
| host              | VARCHAR   | 128  | NO     |        |                 | 主机地址                |
| port              | INTEGER   |      | NO     |        |                 | 端口号                  |
| status            | VARCHAR   | 16   | NO     |        | 'OFFLINE'       | 状态                    |
| group_id          | UUID      |      | YES    | FK     | NULL            | 所属分组ID              |
| max_concurrent    | INTEGER   |      | NO     |        | 5               | 最大并发数              |
| cpu_usage         | DECIMAL   | 5,2  | YES    |        | NULL            | CPU使用率(%)            |
| memory_usage      | DECIMAL   | 5,2  | YES    |        | NULL            | 内存使用率(%)           |
| disk_usage        | DECIMAL   | 5,2  | YES    |        | NULL            | 磁盘使用率(%)           |
| current_tasks     | INTEGER   |      | NO     |        | 0               | 当前任务数              |
| last_heartbeat_at | TIMESTAMP |      | YES    |        | NULL            | 最后心跳时间            |
| is_enabled        | BOOLEAN   |      | NO     |        | true            | 是否启用                |
| created_at        | TIMESTAMP |      | NO     |        | NOW()           | 创建时间                |
| updated_at        | TIMESTAMP |      | NO     |        | NOW()           | 更新时间                |

**状态值：** ONLINE, OFFLINE, BUSY, DISABLED

**索引设计：**
- 主键：`id`
- 索引：`idx_test_nodes_status` (`status`)
- 索引：`idx_test_nodes_group_id` (`group_id`)
- 索引：`idx_test_nodes_is_enabled` (`is_enabled`)
- 索引：`idx_test_nodes_last_heartbeat` (`last_heartbeat_at`)

**表备注：** 测试节点注册与状态管理，心跳30秒上报，90秒未收到标记OFFLINE。

#### 4.3.11 node_groups（节点分组表）

| 字段名       | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明    |
|-------------|-----------|------|--------|--------|-----------------|-----------|
| id          | UUID      |      | NO     | PRI    | gen_random_uuid() | 分组ID     |
| name        | VARCHAR   | 128  | NO     | UNI    |                 | 分组名称    |
| description | TEXT      |      | YES    |        | NULL            | 分组描述    |
| created_at  | TIMESTAMP |      | NO     |        | NOW()           | 创建时间    |
| updated_at  | TIMESTAMP |      | NO     |        | NOW()           | 更新时间    |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_node_groups_name` (`name`)

**表备注：** 节点分组，用于按用途组织节点。

#### 4.3.12 system_logs（系统日志表）

| 字段名         | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明                    |
|---------------|-----------|------|--------|--------|-----------------|----------------------------|
| id            | UUID      |      | NO     | PRI    | gen_random_uuid() | 日志ID                      |
| user_id       | UUID      |      | YES    | FK     | NULL            | 操作人ID                    |
| operation     | VARCHAR   | 32   | NO     |        |                 | 操作类型                     |
| resource_type | VARCHAR   | 32   | NO     |        |                 | 资源类型                     |
| resource_id   | VARCHAR   | 64   | YES    |        | NULL            | 资源ID                       |
| description   | TEXT      |      | YES    |        | NULL            | 操作描述                     |
| ip            | VARCHAR   | 64   | YES    |        | NULL            | 操作IP                       |
| created_at    | TIMESTAMP |      | NO     |        | NOW()           | 创建时间                     |

**操作类型值：** CREATE, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT
**资源类型值：** USER, CASE, TASK, RESULT, NODE, SYSTEM

**索引设计：**
- 主键：`id`
- 索引：`idx_system_logs_user_id` (`user_id`)
- 索引：`idx_system_logs_operation` (`operation`)
- 索引：`idx_system_logs_resource_type` (`resource_type`)
- 索引：`idx_system_logs_created_at` (`created_at` DESC)

**表备注：** 系统操作审计日志，记录所有关键操作。

#### 4.3.13 notifications（通知表）

| 字段名      | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明         |
|------------|-----------|------|--------|--------|-----------------|-----------------|
| id         | UUID      |      | NO     | PRI    | gen_random_uuid() | 通知ID          |
| user_id    | UUID      |      | NO     | FK     |                 | 接收人ID         |
| title      | VARCHAR   | 256  | NO     |        |                 | 通知标题         |
| content    | TEXT      |      | NO     |        |                 | 通知内容         |
| type       | VARCHAR   | 32   | NO     |        | 'SYSTEM'        | 通知类型         |
| is_read    | BOOLEAN   |      | NO     |        | false           | 是否已读         |
| read_at    | TIMESTAMP |      | YES    |        | NULL            | 阅读时间         |
| created_at | TIMESTAMP |      | NO     |        | NOW()           | 创建时间         |

**通知类型值：** TASK_COMPLETE, TASK_FAILED, NODE_OFFLINE, SYSTEM

**索引设计：**
- 主键：`id`
- 索引：`idx_notifications_user_id` (`user_id`, `is_read`, `created_at` DESC)

**表备注：** 平台内消息通知，支持按用户和已读状态查询。

#### 4.3.14 system_configs（系统配置表）

| 字段名       | 数据类型   | 长度 | 允许空 | 键类型 | 默认值           | 字段说明         |
|-------------|-----------|------|--------|--------|-----------------|-----------------|
| id          | UUID      |      | NO     | PRI    | gen_random_uuid() | 配置ID          |
| key         | VARCHAR   | 128  | NO     | UNI    |                 | 配置键           |
| value       | TEXT      |      | NO     |        |                 | 配置值           |
| description | TEXT      |      | YES    |        | NULL            | 配置说明         |
| created_at  | TIMESTAMP |      | NO     |        | NOW()           | 创建时间         |
| updated_at  | TIMESTAMP |      | NO     |        | NOW()           | 更新时间         |

**索引设计：**
- 主键：`id`
- 唯一索引：`uk_system_configs_key` (`key`)

**表备注：** 系统运行参数配置，key-value 结构。

---

## 5. 物理设计

### 5.1 存储分配

- 所有表使用 PostgreSQL 默认表空间
- 大表（system_logs, task_logs, test_results）建议按月分区
- JSONB 字段使用 GIN 索引加速查询

### 5.2 索引设计汇总

| 索引名                           | 表名           | 字段                              | 类型   | 备注              |
|---------------------------------|---------------|-----------------------------------|--------|------------------|
| uk_users_username               | users         | username (WHERE deleted_at IS NULL) | UNIQUE | 用户名唯一        |
| uk_users_email                  | users         | email (WHERE deleted_at IS NULL)    | UNIQUE | 邮箱唯一          |
| uk_roles_code                   | roles         | code                              | UNIQUE | 角色编码唯一      |
| uk_user_roles_user_role         | user_roles    | user_id, role_id                  | UNIQUE | 用户角色唯一关联  |
| idx_test_cases_type             | test_cases    | type (WHERE deleted_at IS NULL)    | B-Tree | 按类型查询        |
| idx_test_cases_status           | test_cases    | status (WHERE deleted_at IS NULL)  | B-Tree | 按状态查询        |
| idx_test_cases_priority         | test_cases    | priority (WHERE deleted_at IS NULL)| B-Tree | 按优先级查询      |
| idx_test_cases_name_gin         | test_cases    | name                              | GIN    | 名称全文搜索      |
| uk_task_cases_task_case         | task_cases    | task_id, case_id                  | UNIQUE | 任务用例唯一关联  |
| idx_tasks_status                | tasks         | status (WHERE deleted_at IS NULL)  | B-Tree | 按状态查询        |
| idx_task_logs_task_id           | task_logs     | task_id, created_at DESC          | B-Tree | 任务日志时序      |
| idx_test_results_task_id        | test_results  | task_id                           | B-Tree | 按任务查结果      |
| uk_test_results_task_case       | test_results  | task_id, case_id                  | UNIQUE | 单任务单用例唯一  |
| uk_result_shares_token          | result_shares | token                             | UNIQUE | 分享Token唯一     |
| idx_test_nodes_status           | test_nodes    | status                            | B-Tree | 按状态查节点      |
| idx_test_nodes_last_heartbeat   | test_nodes    | last_heartbeat_at                 | B-Tree | 心跳超时检测      |
| uk_node_groups_name             | node_groups   | name                              | UNIQUE | 分组名唯一        |
| idx_system_logs_created_at      | system_logs   | created_at DESC                   | B-Tree | 日志时序查询      |
| idx_notifications_user_read     | notifications | user_id, is_read, created_at DESC | B-Tree | 用户未读通知      |
| uk_system_configs_key           | system_configs| key                               | UNIQUE | 配置键唯一        |

### 5.3 数据库参数配置

| 参数                     | 值    | 说明                |
|-------------------------|-------|--------------------|
| max_connections         | 200   | 最大连接数           |
| shared_buffers          | 256MB | 共享缓冲区          |
| work_mem                | 16MB  | 工作内存            |
| maintenance_work_mem    | 128MB | 维护工作内存         |
| effective_cache_size    | 1GB   | 有效缓存大小         |
| log_min_duration_statement | 1000 | 慢查询阈值(ms)     |

---

## 6. 数据安全设计

### 6.1 用户权限

| 用户名/角色     | 数据库对象    | 权限类型                           | 说明           |
|----------------|-------------|-----------------------------------|---------------|
| app_user       | 所有表       | SELECT, INSERT, UPDATE, DELETE    | 应用程序连接用户 |
| admin          | 所有对象     | ALL PRIVILEGES                    | 数据库管理员    |

### 6.2 备份与恢复策略

- **备份类型：** 每日全量备份 + WAL 连续归档
- **备份保留时间：** 30天
- **恢复方式：** pg_basebackup + WAL 重放
- **RPO：** ≤ 5分钟
- **RTO：** ≤ 30分钟

---

## 7. 附录

### 7.1 建表脚本

```sql
-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. users 用户表
-- ============================================================
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(64) NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    email VARCHAR(128) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    login_fail_count INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
CREATE UNIQUE INDEX uk_users_username ON users (username) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uk_users_email ON users (email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_is_active ON users (is_active);

COMMENT ON TABLE users IS '用户表';
COMMENT ON COLUMN users.password_hash IS 'bcrypt加密密码';
COMMENT ON COLUMN users.login_fail_count IS '连续登录失败次数';
COMMENT ON COLUMN users.locked_until IS '锁定截止时间';

-- ============================================================
-- 2. roles 角色表
-- ============================================================
CREATE TABLE roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(32) NOT NULL,
    name VARCHAR(64) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_roles_code ON roles (code);

COMMENT ON TABLE roles IS '角色表';
COMMENT ON COLUMN roles.permissions IS '权限配置，JSONB格式';

-- ============================================================
-- 3. user_roles 用户角色关联表
-- ============================================================
CREATE TABLE user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_user_roles_user_role ON user_roles (user_id, role_id);
CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);

COMMENT ON TABLE user_roles IS '用户角色关联表';

-- ============================================================
-- 4. test_cases 测试用例表
-- ============================================================
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(256) NOT NULL,
    type VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'DRAFT',
    priority VARCHAR(8) NOT NULL DEFAULT 'P2',
    module VARCHAR(128),
    tags JSONB DEFAULT '[]',
    description TEXT,
    preconditions TEXT,
    steps JSONB DEFAULT '[]',
    expected_result TEXT,
    assertions JSONB DEFAULT '[]',
    version INTEGER NOT NULL DEFAULT 1,
    creator_id UUID NOT NULL REFERENCES users(id),
    -- UI用例字段
    ui_url VARCHAR(512),
    ui_script TEXT,
    ui_script_type VARCHAR(32),
    ui_screenshots JSONB DEFAULT '[]',
    ui_video_path VARCHAR(512),
    -- 接口用例字段
    api_url VARCHAR(512),
    api_method VARCHAR(16),
    api_headers JSONB,
    api_body_type VARCHAR(16),
    api_body TEXT,
    api_timeout INTEGER DEFAULT 30000,
    api_assertions JSONB DEFAULT '[]',
    api_dependencies JSONB DEFAULT '[]',
    -- 性能用例字段
    perf_url VARCHAR(512),
    perf_vusers INTEGER,
    perf_spawn_rate INTEGER,
    perf_duration INTEGER,
    perf_locustfile TEXT,
    perf_assertions JSONB DEFAULT '[]',
    -- 通用字段
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
CREATE INDEX idx_test_cases_type ON test_cases (type) WHERE deleted_at IS NULL;
CREATE INDEX idx_test_cases_status ON test_cases (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_test_cases_priority ON test_cases (priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_test_cases_creator_id ON test_cases (creator_id);
CREATE INDEX idx_test_cases_created_at ON test_cases (created_at DESC);

COMMENT ON TABLE test_cases IS '测试用例表';
COMMENT ON COLUMN test_cases.type IS 'UI/API/PERFORMANCE';

-- ============================================================
-- 5. tasks 测试任务表
-- ============================================================
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(256) NOT NULL,
    description TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    priority VARCHAR(8) NOT NULL DEFAULT 'P2',
    execute_type VARCHAR(16) NOT NULL DEFAULT 'IMMEDIATE',
    schedule_cron VARCHAR(64),
    node_id UUID,
    total_cases INTEGER NOT NULL DEFAULT 0,
    success_count INTEGER NOT NULL DEFAULT 0,
    failed_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    creator_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMP
);
CREATE INDEX idx_tasks_status ON tasks (status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_priority ON tasks (priority) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_creator_id ON tasks (creator_id);
CREATE INDEX idx_tasks_created_at ON tasks (created_at DESC);
CREATE INDEX idx_tasks_node_id ON tasks (node_id);

COMMENT ON TABLE tasks IS '测试任务表';
COMMENT ON COLUMN tasks.status IS 'PENDING/SCHEDULED/RUNNING/SUCCESS/FAILED/CANCELLED';

-- ============================================================
-- 6. task_cases 任务用例关联表
-- ============================================================
CREATE TABLE task_cases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    case_id UUID NOT NULL REFERENCES test_cases(id),
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_task_cases_task_case ON task_cases (task_id, case_id);
CREATE INDEX idx_task_cases_case_id ON task_cases (case_id);

COMMENT ON TABLE task_cases IS '任务用例关联表';

-- ============================================================
-- 7. task_logs 任务日志表
-- ============================================================
CREATE TABLE task_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    level VARCHAR(16) NOT NULL DEFAULT 'INFO',
    message TEXT NOT NULL,
    case_id UUID,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_task_logs_task_id ON task_logs (task_id, created_at DESC);
CREATE INDEX idx_task_logs_level ON task_logs (level);

COMMENT ON TABLE task_logs IS '任务日志表';

-- ============================================================
-- 8. test_results 测试结果表
-- ============================================================
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    case_id UUID NOT NULL REFERENCES test_cases(id),
    status VARCHAR(16) NOT NULL,
    detail JSONB DEFAULT '{}',
    duration_ms INTEGER,
    error_message TEXT,
    screenshots JSONB DEFAULT '[]',
    video_path VARCHAR(512),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_test_results_task_id ON test_results (task_id);
CREATE INDEX idx_test_results_case_id ON test_results (case_id);
CREATE INDEX idx_test_results_status ON test_results (status);
CREATE UNIQUE INDEX uk_test_results_task_case ON test_results (task_id, case_id);

COMMENT ON TABLE test_results IS '测试结果表';
COMMENT ON COLUMN test_results.status IS 'SUCCESS/FAILED/SKIPPED/ERROR';

-- ============================================================
-- 9. result_shares 结果分享表
-- ============================================================
CREATE TABLE result_shares (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL REFERENCES tasks(id),
    token VARCHAR(64) NOT NULL,
    password_hash VARCHAR(256),
    expires_at TIMESTAMP,
    creator_id UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_result_shares_token ON result_shares (token);
CREATE INDEX idx_result_shares_task_id ON result_shares (task_id);
CREATE INDEX idx_result_shares_expires_at ON result_shares (expires_at);

COMMENT ON TABLE result_shares IS '结果分享表';

-- ============================================================
-- 10. node_groups 节点分组表
-- ============================================================
CREATE TABLE node_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_node_groups_name ON node_groups (name);

COMMENT ON TABLE node_groups IS '节点分组表';

-- ============================================================
-- 11. test_nodes 测试节点表
-- ============================================================
CREATE TABLE test_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) NOT NULL,
    host VARCHAR(128) NOT NULL,
    port INTEGER NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'OFFLINE',
    group_id UUID REFERENCES node_groups(id),
    max_concurrent INTEGER NOT NULL DEFAULT 5,
    cpu_usage DECIMAL(5,2),
    memory_usage DECIMAL(5,2),
    disk_usage DECIMAL(5,2),
    current_tasks INTEGER NOT NULL DEFAULT 0,
    last_heartbeat_at TIMESTAMP,
    is_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_test_nodes_status ON test_nodes (status);
CREATE INDEX idx_test_nodes_group_id ON test_nodes (group_id);
CREATE INDEX idx_test_nodes_is_enabled ON test_nodes (is_enabled);
CREATE INDEX idx_test_nodes_last_heartbeat ON test_nodes (last_heartbeat_at);

COMMENT ON TABLE test_nodes IS '测试节点表';
COMMENT ON COLUMN test_nodes.status IS 'ONLINE/OFFLINE/BUSY/DISABLED';

-- ============================================================
-- 12. system_logs 系统日志表
-- ============================================================
CREATE TABLE system_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    operation VARCHAR(32) NOT NULL,
    resource_type VARCHAR(32) NOT NULL,
    resource_id VARCHAR(64),
    description TEXT,
    ip VARCHAR(64),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_system_logs_user_id ON system_logs (user_id);
CREATE INDEX idx_system_logs_operation ON system_logs (operation);
CREATE INDEX idx_system_logs_resource_type ON system_logs (resource_type);
CREATE INDEX idx_system_logs_created_at ON system_logs (created_at DESC);

COMMENT ON TABLE system_logs IS '系统日志表';
COMMENT ON COLUMN system_logs.operation IS 'CREATE/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT';
COMMENT ON COLUMN system_logs.resource_type IS 'USER/CASE/TASK/RESULT/NODE/SYSTEM';

-- ============================================================
-- 13. notifications 通知表
-- ============================================================
CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(256) NOT NULL,
    content TEXT NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'SYSTEM',
    is_read BOOLEAN NOT NULL DEFAULT false,
    read_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_notifications_user_read ON notifications (user_id, is_read, created_at DESC);

COMMENT ON TABLE notifications IS '通知表';
COMMENT ON COLUMN notifications.type IS 'TASK_COMPLETE/TASK_FAILED/NODE_OFFLINE/SYSTEM';

-- ============================================================
-- 14. system_configs 系统配置表
-- ============================================================
CREATE TABLE system_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(128) NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE UNIQUE INDEX uk_system_configs_key ON system_configs (key);

COMMENT ON TABLE system_configs IS '系统配置表';
```

### 7.2 初始化数据

```sql
-- 初始化角色
INSERT INTO roles (code, name, permissions) VALUES
('ADMIN', '管理员', '{"user": "CRUD", "case": "CRUD", "task": "CRUD", "result": "RE", "node": "CRUD", "system": "CRUD", "log": "RE"}'),
('TESTER', '测试人员', '{"case": "CRUD", "task": "CRU", "result": "RE", "node": "R", "system": "", "log": ""}'),
('OPS', '运维人员', '{"case": "R", "task": "R", "result": "R", "node": "CRUD", "system": "R", "log": "R"}');

-- 初始化默认管理员（密码：Admin@123456）
INSERT INTO users (username, password_hash, email) VALUES
('admin', '$2b$12$LJ3m4ys3Lz0YBNOURq0Y3OjCfKJmKPOJYqDTPVCKzLOBhZMHfWO6y', 'admin@example.com');

-- 关联管理员角色
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u, roles r WHERE u.username = 'admin' AND r.code = 'ADMIN';

-- 初始化系统配置
INSERT INTO system_configs (key, value, description) VALUES
('login_max_fail_count', '5', '登录失败最大次数'),
('login_lock_duration', '3600', '账号锁定时长(秒)'),
('token_expire_hours', '24', 'Token有效期(小时)'),
('node_heartbeat_interval', '30', '节点心跳间隔(秒)'),
('node_offline_timeout', '90', '节点离线超时(秒)'),
('log_retention_days', '90', '日志保留天数');

-- 初始化默认节点分组
INSERT INTO node_groups (name, description) VALUES
('UI测试组', '负责UI自动化测试'),
('接口测试组', '负责接口自动化测试'),
('性能测试组', '负责性能压测');
```

### 7.3 Redis 缓存设计

| Key 模式 | 数据类型 | 用途 | TTL |
|---------|---------|------|-----|
| `token:blacklist:{token_hash}` | STRING | Token 黑名单 | Token 剩余有效期 |
| `captcha:{email}` | STRING | 邮箱验证码 | 300秒(5分钟) |
| `lock:user:{user_id}` | STRING | 登录锁定标识 | 3600秒(1小时) |
| `cache:config:{key}` | STRING | 系统配置缓存 | 300秒(5分钟) |
| `node:heartbeat:{node_id}` | STRING | 节点心跳标识 | 90秒 |
