# 自动化测试平台 — 系统需求文档

> 版本：1.0 | 日期：2026-05-12 | 基线：user-story.md v1.0

---

## 1. 系统架构概述

```
┌─────────┐     ┌─────────┐     ┌─────────────────────────────────┐
│ Browser │────►│  Nginx  │────►│  Flask Backend (Gunicorn)       │
└─────────┘     │ :80/:443│     │  /api/v1/*                      │
                └─────────┘     │  /ws/*                          │
                                └────────┬──────────┬─────────────┘
                                         │          │
                                   ┌─────▼──┐  ┌───▼────┐
                                   │PostgreSQL│  │ Redis  │
                                   │  :5432  │  │ :6379  │
                                   └─────────┘  └────────┘
                                         │
                          ┌──────────────┼──────────────┐
                          ▼              ▼              ▼
                    ┌──────────┐  ┌──────────┐  ┌──────────┐
                    │ Node-01  │  │ Node-02  │  │ Node-N   │
                    │Playwright│  │Playwright│  │  Locust  │
                    │  Locust  │  │  Locust  │  │          │
                    └──────────┘  └──────────┘  └──────────┘
```

---

## 2. 功能性需求（FR）

### 2.1 身份认证模块（AUTH）

#### FR-AUTH-001 账号密码登录
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/auth/login` |
| 请求体 | `{ "username": string, "password": string }` |
| 响应 | `{ "code": 0, "data": { "token": string, "user": { id, username, role, permissions } } }` |
| 验收标准 | 正确凭证返回 JWT Token；错误凭证返回 401 |

**场景分析：**
| 场景 | 输入 | 预期结果 | HTTP | 错误码 |
|------|------|---------|------|--------|
| 正常登录 | 正确用户名+密码 | 返回 Token 和用户信息 | 200 | - |
| 密码错误 | 正确用户名+错误密码 | 提示"用户名或密码错误" | 401 | INVALID_CREDENTIALS |
| 用户不存在 | 不存在的用户名 | 提示"用户名或密码错误" | 401 | INVALID_CREDENTIALS |
| 账号禁用 | 已禁用账号 | 提示"账号已禁用" | 403 | ACCOUNT_DISABLED |
| 账号锁定 | 连续5次失败后 | 提示"账号已锁定" | 423 | ACCOUNT_LOCKED |
| 密码复杂度不足 | 密码<8位或缺少字符类型 | 参数校验失败 | 422 | VALIDATION_ERROR |

#### FR-AUTH-002 退出登录
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/auth/logout` |
| 认证 | 需要 Bearer Token |
| 响应 | Token 加入 Redis 黑名单，有效期 = Token 剩余有效期 |

#### FR-AUTH-003 Token 刷新
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `POST /api/v1/auth/refresh-token` |
| 行为 | 使用当前有效 Token 获取新 Token，旧 Token 立即失效 |

#### FR-AUTH-004 获取当前用户信息
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/auth/me` |
| 响应 | 用户 ID、用户名、角色、权限列表 |

#### FR-AUTH-005 密码找回
| 属性 | 值 |
|------|-----|
| 优先级 | P2 |
| API | `POST /api/v1/auth/forgot-password` → `POST /api/v1/auth/verify-code` → `POST /api/v1/auth/reset-password` |
| 流程 | 发送验证码 → 验证 → 重置密码 |
| 验证码有效期 | 5 分钟，存储于 Redis |

#### FR-AUTH-006 权限控制
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| 实现 | 基于角色的访问控制（RBAC），通过 `require_roles()` 装饰器实现 |
| 角色 | ADMIN（管理员）、TESTER（测试人员）、OPS（运维人员） |
| 权限矩阵 | 见下表 |

**权限矩阵：**

| 功能 | ADMIN | TESTER | OPS |
|------|-------|--------|-----|
| 用户管理 | CRUD | - | - |
| 用例管理 | CRUD | CRUD | R |
| 任务管理 | CRUD | CRU | R |
| 结果查看 | R+E | R+E | R |
| 节点管理 | CRUD | R | CRUD |
| 系统配置 | CRUD | - | R |
| 系统日志 | R+E | - | R |

> R=读取, C=创建, U=更新, D=删除, E=导出

---

### 2.2 用例管理模块（CASE）

#### FR-CASE-001 用例列表查询
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/cases` |
| 查询参数 | `page`, `pageSize`, `type`, `status`, `priority`, `keyword` |
| 响应 | 分页用例列表 + 分页信息 |

**场景分析：**
| 场景 | 预期结果 |
|------|---------|
| 无筛选条件 | 返回全部用例，按创建时间倒序 |
| 按类型筛选 `type=API` | 仅返回接口测试用例 |
| 关键词搜索 `keyword=登录` | 模糊匹配用例名称 |
| 组合筛选 `type=UI&priority=P1` | 返回同时满足条件的用例 |
| 空结果 | 返回空列表，total=0 |

#### FR-CASE-002 创建用例
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/cases` |
| 请求体 | 见下表 |
| 响应 | `{ "code": 0, "data": { "id": string } }` |

**用例数据模型：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string(256) | 是 | 用例名称 |
| type | enum | 是 | UI / API / PERFORMANCE |
| priority | enum | 否 | P0/P1/P2/P3，默认 P2 |
| status | enum | 否 | DRAFT/ACTIVE/DEPRECATED，默认 DRAFT |
| module | string(128) | 否 | 所属模块 |
| tags | json[] | 否 | 标签列表 |
| description | text | 否 | 用例描述 |
| preconditions | text | 否 | 前置条件 |
| steps | json[] | 否 | 执行步骤 |
| expected_result | text | 否 | 预期结果 |
| assertions | json[] | 否 | 断言规则 |

**UI 用例扩展字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| ui_url | string(512) | 目标页面 URL |
| ui_script | text | Playwright 脚本内容 |
| ui_script_type | enum | RECORDED（录制）/ MANUAL（手动） |
| ui_screenshots | json[] | 关键步骤截图路径 |
| ui_video_path | string | 执行录像路径 |

**接口用例扩展字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| api_url | string(512) | 接口地址 |
| api_method | enum | GET/POST/PUT/DELETE/PATCH |
| api_headers | json | 请求头 |
| api_body_type | enum | NONE/JSON/FORM/XML/RAW |
| api_body | text | 请求体 |
| api_timeout | int | 超时时间(ms)，默认 30000 |
| api_assertions | json[] | 断言规则（状态码/响应内容/响应时间） |
| api_dependencies | json[] | 接口依赖配置 |

**性能用例扩展字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| perf_url | string(512) | 压测目标 URL |
| perf_vusers | int | 并发用户数 |
| perf_spawn_rate | int | 用户增长率(用户/秒) |
| perf_duration | int | 持续时间(秒) |
| perf_locustfile | text | Locust 脚本内容 |
| perf_assertions | json[] | 性能断言（P95≤500ms, 错误率≤1%等） |

#### FR-CASE-003 更新用例
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `PUT /api/v1/cases/{case_id}` |
| 行为 | 更新指定字段，version 自动递增 |

#### FR-CASE-004 删除用例
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `DELETE /api/v1/cases/{case_id}` |
| 权限 | 仅 ADMIN |
| 行为 | 软删除（设置 deleted_at） |

#### FR-CASE-005 用例导入导出
| 属性 | 值 |
|------|-----|
| 优先级 | P2 |
| API | `POST /api/v1/cases/export` / `POST /api/v1/cases/import` |
| 格式 | Excel (.xlsx) / JSON |

#### FR-CASE-006 用例版本管理
| 属性 | 值 |
|------|-----|
| 优先级 | P2 |
| API | `GET /api/v1/cases/{case_id}/versions` / `POST /api/v1/cases/{case_id}/rollback` |
| 行为 | 每次修改记录版本，支持查看历史和回滚 |

---

### 2.3 任务管理模块（TASK）

#### FR-TASK-001 创建任务
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/tasks` |
| 请求体 | `{ name, description?, priority, case_ids[], execute_type?, node_id?, schedule_cron? }` |
| 响应 | `{ "code": 0, "data": { "id": string } }` |

**场景分析：**
| 场景 | 预期结果 |
|------|---------|
| 立即执行 | 任务创建后状态为 PENDING，进入调度队列 |
| 定时执行 | 任务状态为 SCHEDULED，记录 cron 表达式 |
| 空用例列表 | 参数校验失败，提示"至少选择一个用例" |
| 选用例>100 | 参数校验失败，提示"单任务最多100个用例" |

#### FR-TASK-002 任务调度
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| 行为 | 后台调度器按优先级从队列取任务，分配到可用节点执行 |
| 调度策略 | 1. 按优先级排序 2. 选择负载最低的可用节点 3. 检查节点并发上限 |

#### FR-TASK-003 任务状态管理
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/tasks/{id}/start` / `POST /api/v1/tasks/{id}/cancel` |

**状态机：**
```
PENDING ──start──► RUNNING ──complete──► SUCCESS
   │                  │                    │
   │                  ├──fail──► FAILED    │
   │                  │                    │
   └──cancel──► CANCELLED ◄──cancel───────┘
```

#### FR-TASK-004 任务日志
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `GET /api/v1/tasks/{id}/logs` |
| 存储 | task_logs 表，记录时间戳、级别、消息 |

---

### 2.4 测试执行引擎

#### FR-EXEC-001 Playwright UI 测试执行
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| 引擎 | Playwright (Python) |
| 执行流程 | 1. 从用例读取脚本 2. 创建浏览器上下文 3. 执行脚本 4. 采集截图/录像 5. 解析断言结果 6. 写入结果表 |
| 浏览器支持 | Chromium, Firefox, WebKit |
| 超时控制 | 单用例默认 60s，可配置 |
| 截图策略 | 每个断言步骤自动截图，失败时额外截图 |
| 录像策略 | 失败用例自动录制执行过程 |

#### FR-EXEC-002 接口测试执行
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| 引擎 | Python requests / httpx |
| 执行流程 | 1. 解析用例配置 2. 处理接口依赖 3. 发送请求 4. 执行断言 5. 写入结果 |
| 断言类型 | 状态码、响应体 JSONPath、响应时间、响应头 |
| 依赖处理 | 支持 JSONPath 提取前置接口返回值，注入后续请求参数 |

#### FR-EXEC-003 Locust 性能压测执行
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| 引擎 | Locust (Python) |
| 执行流程 | 1. 从用例生成 locustfile 2. 分发到节点 3. 启动压测 4. 实时采集指标 5. 生成报告 6. 写入结果 |
| 分布式执行 | 支持 master + worker 模式，跨节点分配负载 |
| 采集指标 | RPS、响应时间(P50/P95/P99)、失败率、用户数 |
| 报告格式 | HTML (Locust 原生) + 自定义结构化数据 |

#### FR-EXEC-004 UI 用例录制
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| 实现 | 基于 Playwright Codegen 集成录制器功能 |
| 流程 | 1. 启动录制浏览器 2. 用户操作 3. 实时生成 Playwright 代码 4. 保存为用例脚本 |
| 输出 | Python Playwright 脚本，支持编辑和回放 |

---

### 2.5 结果展示模块（RESULT）

#### FR-RESULT-001 结果概览
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/results/overview?taskId={id}` |
| 响应 | `{ totalCases, successCount, failedCount, skippedCount, successRate, duration }` |

#### FR-RESULT-002 结果列表
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/results?taskId={id}&page=&pageSize=&status=` |
| 响应 | 分页结果列表，每条包含用例名、类型、状态、耗时、时间 |

#### FR-RESULT-003 结果详情
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/results/api/{result_id}` |
| 响应 | 详细结果：请求/响应信息、断言结果、截图路径、错误日志 |

#### FR-RESULT-004 结果导出
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `POST /api/v1/results/{task_id}/export` |
| 格式 | Excel / PDF / HTML |

#### FR-RESULT-005 结果分享
| 属性 | 值 |
|------|-----|
| 优先级 | P2 |
| API | `POST /api/v1/results/{task_id}/share` → `GET /api/v1/results/share/{token}` |
| 行为 | 生成带 Token 的分享链接，支持设置有效期和访问密码 |

---

### 2.6 节点管理模块（NODE）

#### FR-NODE-001 节点注册
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/nodes`（手动录入）/ 客户端自动注册 |
| 数据 | name, host, port, group_id, max_concurrent |

#### FR-NODE-002 节点列表
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /api/v1/nodes?page=&pageSize=&status=&keyword=` |
| 响应 | 节点列表：名称、地址、状态、CPU/内存/磁盘使用率、当前任务数 |

#### FR-NODE-003 节点心跳
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `POST /api/v1/nodes/{id}/heartbeat` |
| 行为 | 客户端每30秒上报心跳，服务端更新 last_heartbeat_at 和资源指标 |
| 离线判定 | 超过90秒未收到心跳 → 标记为 OFFLINE |

#### FR-NODE-004 节点分组
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `GET /api/v1/nodes/groups` |
| 行为 | 支持创建/编辑/删除节点组，节点归属一个组 |

#### FR-NODE-005 节点禁用/启用
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `PUT /api/v1/nodes/{id}` |
| 行为 | 禁用后不再分配新任务，已有任务继续完成 |

---

### 2.7 系统管理模块（SYS）

#### FR-SYS-001 操作日志
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `GET /api/v1/system/logs?page=&pageSize=&operation=` |
| 记录内容 | 操作人、操作类型、资源类型、资源ID、描述、IP、时间 |
| 操作类型 | CREATE / UPDATE / DELETE / LOGIN / LOGOUT / EXPORT |
| 资源类型 | USER / CASE / TASK / RESULT / NODE / SYSTEM |

#### FR-SYS-002 消息通知
| 属性 | 值 |
|------|-----|
| 优先级 | P2 |
| API | `GET /api/v1/system/notifications` / `PUT /api/v1/system/notifications/{id}/read` |
| 触发场景 | 任务完成/失败、节点离线、权限变更 |
| 通知方式 | 平台内消息（P0）、邮件（P2） |

#### FR-SYS-003 系统配置
| 属性 | 值 |
|------|-----|
| 优先级 | P1 |
| API | `GET /api/v1/system/config` / `PUT /api/v1/system/config` |
| 配置项 | 登录失败限制、锁定时长、Token有效期、节点心跳间隔、日志保留天数 |

#### FR-SYS-004 健康检查
| 属性 | 值 |
|------|-----|
| 优先级 | P0 |
| API | `GET /health` / `GET /ready` |
| 行为 | 无需认证，返回服务状态 |

---

## 3. 非功能性需求（NFR）

### 3.1 性能

| NFR | 指标 | 验证方式 |
|-----|------|---------|
| NFR-PERF-001 | 并发任务数 ≥ 50 | 压测验证 |
| NFR-PERF-002 | 页面加载 ≤ 2s | Lighthouse 测试 |
| NFR-PERF-003 | API 响应 ≤ 1s (P95) | 压测验证 |
| NFR-PERF-004 | 单表 10 万条查询 ≤ 3s | 数据填充测试 |
| NFR-PERF-005 | 平台 7×24 无崩溃 | 稳定性测试 |
| NFR-PERF-006 | 任务执行成功率 ≥ 99% | 统计验证 |

### 3.2 安全

| NFR | 要求 |
|-----|------|
| NFR-SEC-001 | 密码 bcrypt 加密存储 |
| NFR-SEC-002 | JWT Token 认证，支持黑名单 |
| NFR-SEC-003 | RBAC 角色权限控制 |
| NFR-SEC-004 | 输入参数校验（Pydantic），防 SQL 注入 |
| NFR-SEC-005 | CORS 白名单控制 |
| NFR-SEC-006 | HTTPS 支持（Nginx SSL 终端） |
| NFR-SEC-007 | 数据落盘到宿主机指定目录，支持迁移 |

### 3.3 日志

| NFR | 要求 |
|-----|------|
| NFR-LOG-001 | 按模块分日志文件：`data/YYYYMMDD/module/xxx.log` |
| NFR-LOG-002 | 单文件最大 10MB，超过自动轮转 |
| NFR-LOG-003 | 日志级别可配置（DEBUG/INFO/WARNING/ERROR） |
| NFR-LOG-004 | 日志总开关可关闭 |
| NFR-LOG-005 | 容器日志统一映射到宿主机 `/opt/auto-test/logs/` |
| NFR-LOG-006 | 业务操作埋点记录 |

### 3.4 可扩展性

| NFR | 要求 |
|-----|------|
| NFR-EXT-001 | 支持新增测试类型（如 APP 测试），无需重构核心代码 |
| NFR-EXT-002 | 测试节点横向扩充，新节点即插即用 |
| NFR-EXT-003 | 支持与 Jira/Jenkins 等工具集成 |

### 3.5 可维护性

| NFR | 要求 |
|-----|------|
| NFR-MAINT-001 | 代码规范，注释清晰 |
| NFR-MAINT-002 | 完善的系统日志和错误日志 |
| NFR-MAINT-003 | 版本平滑更新，不影响正在执行的任务 |
| NFR-MAINT-004 | Docker 容器化部署，支持一键启动 |

### 3.6 兼容性

| NFR | 要求 |
|-----|------|
| NFR-COMP-001 | 前端支持 Chrome/Firefox/Edge 最新两个大版本 |
| NFR-COMP-002 | 响应式布局，适配 1280px 及以上屏幕 |
| NFR-COMP-003 | 测试节点支持 Windows/Linux/macOS |

---

## 4. 数据模型

### 4.1 核心实体关系

```
User ──1:N── UserRole ──N:1── Role
  │
  ├──1:N── TestCase ──N:M── TaskCase ──N:1── Task
  │                                    │
  ├──1:N── TestResult ◄────────────────┘
  │           │
  │           └──1:N── ResultShare
  │
  ├──1:N── TestNode ──N:1── NodeGroup
  │
  ├──1:N── SystemLog
  ├──1:N── Notification
  └──1:N── SystemConfig
```

### 4.2 核心表

| 表名 | 说明 | 核心字段 |
|------|------|---------|
| users | 用户表 | username, password_hash, email, is_active, login_fail_count, locked_until |
| roles | 角色表 | code, name, permissions(jsonb) |
| user_roles | 用户角色关联 | user_id, role_id |
| test_cases | 测试用例表 | name, type, status, priority, steps(jsonb), ui_script, api_*, perf_* |
| task_cases | 任务用例关联 | task_id, case_id, sort_order |
| tasks | 测试任务表 | name, status, priority, total_cases, success_count, failed_count |
| task_logs | 任务日志表 | task_id, level, message, timestamp |
| test_results | 测试结果表 | task_id, case_id, status, detail(jsonb), duration_ms |
| result_shares | 结果分享表 | result_id, token, password_hash, expires_at |
| test_nodes | 测试节点表 | name, host, port, status, cpu_usage, memory_usage, last_heartbeat_at |
| node_groups | 节点分组表 | name, description |
| system_logs | 系统日志表 | user_id, operation, resource_type, resource_id, description, ip |
| notifications | 通知表 | user_id, title, content, is_read, read_at |
| system_configs | 系统配置表 | key, value, description |

---

## 5. API 汇总

| 模块 | API 数量 | 核心接口 |
|------|---------|---------|
| 认证 (AUTH) | 7 | login, logout, refresh-token, me, forgot/verify/reset-password |
| 用例 (CASE) | 8 | CRUD, import, export, versions, rollback |
| 任务 (TASK) | 8 | CRUD, start, cancel, logs, schedule |
| 结果 (RESULT) | 5 | overview, list, detail, export, share |
| 节点 (NODE) | 7 | CRUD, heartbeat, groups, disable/enable |
| 系统 (SYS) | 6 | logs, notifications, config, stats, health, ready |
| **合计** | **41** | |

---

## 6. 错误码定义

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

## 7. 待澄清事项

| # | 问题 | 影响范围 |
|---|------|---------|
| 2 | Locust 分布式执行是否需要 master-worker 模式？还是单节点即可？----aster-worker模式 | FR-EXEC-003 架构设计 |
| 3 | 邮件通知需要配置 SMTP 服务器，是否在本次迭代？----后续功能开发 | FR-SYS-002 范围 |
| 4 | 节点客户端/代理的具体实现方式？是独立程序还是容器？---容器 | FR-NODE-001 实现 |
| 5 | 日志按模块分文件的具体模块划分？--按照平台业务功能模块区分 | NFR-LOG-001 实现 |
