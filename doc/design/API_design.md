# 自动化测试平台 — API 接口设计文档

**文档版本：** V1.0
**创建日期：** 2026-05-12
**最后修改日期：** 2026-05-12

---

## 修订历史

| 版本 | 日期       | 修改说明 | 修改人 | 审核人 |
|------|-----------|---------|--------|--------|
| V1.0 | 2026-05-12 | 初始创建 | -      | -      |

---

## 1. 概述

### 1.1 编写目的

本文档定义自动化测试平台所有 RESTful API 接口的规格说明，为前后端开发和联调提供接口契约。

### 1.2 适用范围

覆盖认证、用例管理、任务管理、测试结果、节点管理、系统管理六个模块共 41 个 API。

### 1.3 技术栈

- **后端框架：** Flask + Python
- **Web 服务器：** Gunicorn
- **反向代理：** Nginx
- **数据库：** PostgreSQL
- **缓存：** Redis

---

## 2. 通用规范

### 2.1 基础 URL

```
http(s)://{host}/api/v1
```

### 2.2 请求格式

- **Content-Type：** `application/json; charset=UTF-8`
- **字符编码：** UTF-8
- **时间格式：** ISO 8601（`2026-05-12T10:30:00Z`）

### 2.3 统一响应格式

```json
{
    "code": 0,
    "message": "success",
    "data": {}
}
```

**成功响应：**
```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

**错误响应：**
```json
{
    "code": "ERROR_CODE",
    "message": "错误描述信息",
    "data": null
}
```

### 2.4 分页响应格式

```json
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [],
        "total": 100,
        "page": 1,
        "page_size": 20
    }
}
```

**分页参数：**

| 参数       | 类型 | 必填 | 默认值 | 说明        |
|-----------|------|------|--------|-----------|
| page      | int  | 否   | 1      | 页码       |
| page_size | int  | 否   | 20     | 每页条数(10/20/50) |

### 2.5 认证方式

- **类型：** JWT Bearer Token
- **Header：** `Authorization: Bearer <token>`
- **Token 有效期：** 24小时（可配置）
- **Token 刷新：** 使用有效 Token 调用 `/auth/refresh-token` 获取新 Token
- **Token 失效：** 退出登录时 Token 加入 Redis 黑名单

### 2.6 错误码定义

| 错误码                   | HTTP | 说明               |
|-------------------------|------|-------------------|
| INVALID_CREDENTIALS     | 401  | 用户名或密码错误    |
| ACCOUNT_DISABLED        | 403  | 账号已禁用          |
| ACCOUNT_LOCKED          | 423  | 账号已锁定          |
| TOKEN_INVALID           | 401  | Token 无效         |
| TOKEN_REVOKED           | 401  | Token 已失效       |
| FORBIDDEN               | 403  | 权限不足            |
| CASE_NOT_FOUND          | 404  | 用例不存在          |
| TASK_NOT_FOUND          | 404  | 任务不存在          |
| RESULT_NOT_FOUND        | 404  | 结果不存在          |
| NODE_NOT_FOUND          | 404  | 节点不存在          |
| SHARE_NOT_FOUND         | 404  | 分享链接不存在      |
| SHARE_EXPIRED           | 410  | 分享链接已过期      |
| SHARE_PASSWORD_REQUIRED | 401  | 需要访问密码        |
| SHARE_PASSWORD_INVALID  | 401  | 密码错误            |
| VALIDATION_ERROR        | 422  | 参数校验失败        |
| INTERNAL_ERROR          | 500  | 服务器内部错误      |

### 2.7 RBAC 权限矩阵

| 功能     | ADMIN | TESTER | OPS |
|---------|-------|--------|-----|
| 用户管理  | CRUD  | -      | -   |
| 用例管理  | CRUD  | CRUD   | R   |
| 任务管理  | CRUD  | CRU    | R   |
| 结果查看  | R+E   | R+E    | R   |
| 节点管理  | CRUD  | R      | CRUD|
| 系统配置  | CRUD  | -      | R   |
| 系统日志  | R+E   | -      | R   |

> R=读取, C=创建, U=更新, D=删除, E=导出

---

## 3. 认证模块（AUTH）

### 3.1 POST /api/v1/auth/login — 账号密码登录

**认证：** 无需
**权限：** 无

#### 请求参数（Body）

| 参数名    | 类型   | 必填 | 说明            |
|----------|--------|------|----------------|
| username | string | 是   | 用户名          |
| password | string | 是   | 密码            |

#### 响应参数

| 参数名              | 类型   | 说明                    |
|--------------------|--------|------------------------|
| token              | string | JWT Token              |
| user               | object | 用户信息                |
| user.id            | string | 用户ID                 |
| user.username      | string | 用户名                 |
| user.role          | string | 角色编码                |
| user.permissions   | object | 权限配置               |

#### 场景

**正常登录：**
```json
// 请求
POST /api/v1/auth/login
{ "username": "admin", "password": "Admin@123456" }

// 响应 200
{
    "code": 0,
    "message": "success",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIs...",
        "user": {
            "id": "uuid-string",
            "username": "admin",
            "role": "ADMIN",
            "permissions": { "case": "CRUD", "task": "CRUD" }
        }
    }
}
```

**密码错误：**
```json
// 响应 401
{ "code": "INVALID_CREDENTIALS", "message": "用户名或密码错误", "data": null }
```

**账号锁定：**
```json
// 响应 423
{ "code": "ACCOUNT_LOCKED", "message": "账号已锁定，请58分钟后重试", "data": null }
```

**账号禁用：**
```json
// 响应 403
{ "code": "ACCOUNT_DISABLED", "message": "账号已禁用", "data": null }
```

---

### 3.2 POST /api/v1/auth/logout — 退出登录

**认证：** 需要 Bearer Token
**权限：** 所有角色

#### 响应

```json
// 200
{ "code": 0, "message": "success", "data": null }
```

**行为：** 将当前 Token 加入 Redis 黑名单，TTL = Token 剩余有效期。

---

### 3.3 POST /api/v1/auth/refresh-token — Token 刷新

**认证：** 需要 Bearer Token
**权限：** 所有角色

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": { "token": "new-jwt-token" }
}
```

**行为：** 使用当前有效 Token 获取新 Token，旧 Token 立即失效（加入黑名单）。

---

### 3.4 GET /api/v1/auth/me — 获取当前用户信息

**认证：** 需要 Bearer Token
**权限：** 所有角色

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "id": "uuid-string",
        "username": "admin",
        "email": "admin@example.com",
        "role": "ADMIN",
        "permissions": { "case": "CRUD", "task": "CRUD" },
        "is_active": true,
        "created_at": "2026-05-12T10:00:00Z"
    }
}
```

---

### 3.5 POST /api/v1/auth/forgot-password — 发送验证码

**认证：** 无需
**权限：** 无

#### 请求参数（Body）

| 参数名  | 类型   | 必填 | 说明   |
|--------|--------|------|-------|
| email  | string | 是   | 绑定邮箱 |

#### 响应

```json
// 200
{ "code": 0, "message": "验证码已发送", "data": null }
```

**行为：** 向绑定邮箱发送6位数字验证码，有效期5分钟，存储于 Redis。

---

### 3.6 POST /api/v1/auth/verify-code — 验证验证码

**认证：** 无需
**权限：** 无

#### 请求参数（Body）

| 参数名  | 类型   | 必填 | 说明   |
|--------|--------|------|-------|
| email  | string | 是   | 绑定邮箱 |
| code   | string | 是   | 6位验证码 |

#### 响应

```json
// 200
{ "code": 0, "message": "验证成功", "data": { "reset_token": "xxx" } }
```

---

### 3.7 POST /api/v1/auth/reset-password — 重置密码

**认证：** 无需（使用 reset_token）
**权限：** 无

#### 请求参数（Body）

| 参数名       | 类型   | 必填 | 说明                |
|-------------|--------|------|--------------------|
| reset_token | string | 是   | 验证码验证后获得的token |
| new_password| string | 是   | 新密码（≥8位，含字母+数字+特殊符号） |

#### 响应

```json
// 200
{ "code": 0, "message": "密码重置成功", "data": null }
```

---

## 4. 用例管理模块（CASE）

### 4.1 GET /api/v1/cases — 用例列表查询

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD), OPS(R)

#### 查询参数

| 参数名    | 类型   | 必填 | 说明                              |
|----------|--------|------|----------------------------------|
| page     | int    | 否   | 页码，默认1                       |
| page_size| int    | 否   | 每页条数，默认20                   |
| type     | string | 否   | 类型筛选：UI/API/PERFORMANCE      |
| status   | string | 否   | 状态筛选：DRAFT/ACTIVE/DEPRECATED |
| priority | string | 否   | 优先级筛选：P0/P1/P2/P3           |
| keyword  | string | 否   | 关键词搜索（模糊匹配用例名称）      |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "name": "登录功能测试",
                "type": "UI",
                "status": "ACTIVE",
                "priority": "P1",
                "module": "认证模块",
                "tags": ["冒烟测试"],
                "version": 3,
                "creator": { "id": "uuid", "username": "tester1" },
                "created_at": "2026-05-12T10:00:00Z",
                "updated_at": "2026-05-12T15:00:00Z"
            }
        ],
        "total": 150,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 4.2 POST /api/v1/cases — 创建用例

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 请求参数（Body）

| 参数名           | 类型     | 必填 | 说明                    |
|-----------------|----------|------|------------------------|
| name            | string   | 是   | 用例名称（≤256字符）     |
| type            | string   | 是   | UI/API/PERFORMANCE      |
| priority        | string   | 否   | P0/P1/P2/P3，默认P2     |
| status          | string   | 否   | DRAFT/ACTIVE，默认DRAFT  |
| module          | string   | 否   | 所属模块                 |
| tags            | string[] | 否   | 标签列表                 |
| description     | string   | 否   | 用例描述                 |
| preconditions   | string   | 否   | 前置条件                 |
| steps           | object[] | 否   | 执行步骤                 |
| expected_result | string   | 否   | 预期结果                 |
| assertions      | object[] | 否   | 断言规则                 |

**UI 用例扩展字段：**

| 参数名           | 类型   | 必填 | 说明                  |
|-----------------|--------|------|----------------------|
| ui_url          | string | 否   | 目标页面URL            |
| ui_script       | string | 否   | Playwright脚本内容    |
| ui_script_type  | string | 否   | RECORDED/MANUAL      |

**接口用例扩展字段：**

| 参数名           | 类型   | 必填 | 说明                           |
|-----------------|--------|------|-------------------------------|
| api_url         | string | 否   | 接口地址                       |
| api_method      | string | 否   | GET/POST/PUT/DELETE/PATCH      |
| api_headers     | object | 否   | 请求头                         |
| api_body_type   | string | 否   | NONE/JSON/FORM/XML/RAW        |
| api_body        | string | 否   | 请求体                         |
| api_timeout     | int    | 否   | 超时时间(ms)，默认30000         |
| api_assertions  | object[]| 否  | 断言规则                       |
| api_dependencies| object[]| 否  | 接口依赖配置                   |

**性能用例扩展字段：**

| 参数名           | 类型   | 必填 | 说明               |
|-----------------|--------|------|-------------------|
| perf_url        | string | 否   | 压测目标URL        |
| perf_vusers     | int    | 否   | 并发用户数          |
| perf_spawn_rate | int    | 否   | 用户增长率          |
| perf_duration   | int    | 否   | 持续时间(秒)       |
| perf_locustfile | string | 否   | Locust脚本内容     |
| perf_assertions | object[]| 否  | 性能断言规则       |

#### 响应

```json
// 201
{ "code": 0, "message": "创建成功", "data": { "id": "uuid" } }
```

---

### 4.3 PUT /api/v1/cases/{case_id} — 更新用例

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 路径参数

| 参数名   | 类型   | 说明   |
|---------|--------|-------|
| case_id | string | 用例ID |

#### 请求参数（Body）

同创建用例，所有字段均为可选（部分更新）。

#### 响应

```json
// 200
{ "code": 0, "message": "更新成功", "data": { "id": "uuid", "version": 4 } }
```

**行为：** 更新指定字段，version 自动递增，记录版本历史。

---

### 4.4 DELETE /api/v1/cases/{case_id} — 删除用例

**认证：** 需要 Bearer Token
**权限：** 仅 ADMIN

#### 路径参数

| 参数名   | 类型   | 说明   |
|---------|--------|-------|
| case_id | string | 用例ID |

#### 响应

```json
// 200
{ "code": 0, "message": "删除成功", "data": null }
```

**行为：** 软删除（设置 deleted_at），不物理删除数据。

---

### 4.5 POST /api/v1/cases/export — 导出用例

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 请求参数（Body）

| 参数名    | 类型     | 必填 | 说明                      |
|----------|----------|------|--------------------------|
| format   | string   | 是   | 导出格式：EXCEL/JSON      |
| case_ids | string[] | 否   | 指定用例ID列表，为空则导出全部 |
| type     | string   | 否   | 按类型筛选                 |

#### 响应

```json
// 200（文件下载）
Content-Type: application/octet-stream
Content-Disposition: attachment; filename=cases_export.xlsx
```

---

### 4.6 POST /api/v1/cases/import — 导入用例

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 请求参数（multipart/form-data）

| 参数名  | 类型 | 必填 | 说明                   |
|--------|------|------|-----------------------|
| file   | file | 是   | Excel(.xlsx)或JSON文件 |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "导入成功",
    "data": { "imported": 50, "skipped": 2, "errors": [] }
}
```

---

### 4.7 GET /api/v1/cases/{case_id}/versions — 用例版本历史

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 路径参数

| 参数名   | 类型   | 说明   |
|---------|--------|-------|
| case_id | string | 用例ID |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "version": 3,
                "modifier": { "id": "uuid", "username": "tester1" },
                "changes": { "name": { "old": "旧名称", "new": "新名称" } },
                "created_at": "2026-05-12T15:00:00Z"
            }
        ],
        "total": 3,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 4.8 POST /api/v1/cases/{case_id}/rollback — 用例回滚

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRUD)

#### 路径参数

| 参数名   | 类型   | 说明   |
|---------|--------|-------|
| case_id | string | 用例ID |

#### 请求参数（Body）

| 参数名  | 类型 | 必填 | 说明         |
|--------|------|------|-------------|
| version| int  | 是   | 目标版本号    |

#### 响应

```json
// 200
{ "code": 0, "message": "回滚成功", "data": { "id": "uuid", "version": 4 } }
```

**行为：** 用例内容恢复到指定版本，当前版本号递增（不回退版本号）。

---

## 5. 任务管理模块（TASK）

### 5.1 GET /api/v1/tasks — 任务列表

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU), OPS(R)

#### 查询参数

| 参数名    | 类型   | 必填 | 说明                                  |
|----------|--------|------|--------------------------------------|
| page     | int    | 否   | 页码                                 |
| page_size| int    | 否   | 每页条数                              |
| status   | string | 否   | 状态筛选：PENDING/SCHEDULED/RUNNING/SUCCESS/FAILED/CANCELLED |
| priority | string | 否   | 优先级筛选                            |
| keyword  | string | 否   | 任务名称模糊搜索                       |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "name": "回归测试-登录模块",
                "status": "RUNNING",
                "priority": "P1",
                "execute_type": "IMMEDIATE",
                "total_cases": 20,
                "success_count": 15,
                "failed_count": 2,
                "creator": { "id": "uuid", "username": "tester1" },
                "started_at": "2026-05-12T10:00:00Z",
                "created_at": "2026-05-12T09:55:00Z"
            }
        ],
        "total": 50,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 5.2 POST /api/v1/tasks — 创建任务

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU)

#### 请求参数（Body）

| 参数名         | 类型     | 必填 | 说明                              |
|---------------|----------|------|----------------------------------|
| name          | string   | 是   | 任务名称（≤256字符）               |
| description   | string   | 否   | 任务描述                          |
| priority      | string   | 否   | 优先级：P0/P1/P2/P3，默认P2       |
| case_ids      | string[] | 是   | 用例ID列表（1~100个）              |
| execute_type  | string   | 否   | IMMEDIATE/SCHEDULED，默认IMMEDIATE |
| node_id       | string   | 否   | 指定执行节点ID                     |
| schedule_cron | string   | 否   | Cron表达式（execute_type=SCHEDULED时必填） |

#### 场景

**立即执行：**
```json
// 请求
POST /api/v1/tasks
{
    "name": "回归测试-登录模块",
    "priority": "P1",
    "case_ids": ["case-uuid-1", "case-uuid-2"],
    "execute_type": "IMMEDIATE"
}

// 响应 201
{ "code": 0, "message": "创建成功", "data": { "id": "task-uuid" } }
```

**空用例列表：**
```json
// 响应 422
{ "code": "VALIDATION_ERROR", "message": "至少选择一个用例", "data": null }
```

**用例超过100个：**
```json
// 响应 422
{ "code": "VALIDATION_ERROR", "message": "单任务最多100个用例", "data": null }
```

---

### 5.3 GET /api/v1/tasks/{id} — 任务详情

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU), OPS(R)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "id": "uuid",
        "name": "回归测试-登录模块",
        "description": "登录相关用例回归",
        "status": "RUNNING",
        "priority": "P1",
        "execute_type": "IMMEDIATE",
        "total_cases": 20,
        "success_count": 15,
        "failed_count": 2,
        "cases": [
            { "id": "case-uuid", "name": "登录功能测试", "status": "SUCCESS", "sort_order": 1 }
        ],
        "creator": { "id": "uuid", "username": "tester1" },
        "started_at": "2026-05-12T10:00:00Z",
        "completed_at": null,
        "created_at": "2026-05-12T09:55:00Z"
    }
}
```

---

### 5.4 PUT /api/v1/tasks/{id} — 更新任务

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 请求参数（Body）

仅 PENDING/SCHEDULED 状态的任务可更新。

| 参数名         | 类型   | 必填 | 说明         |
|---------------|--------|------|-------------|
| name          | string | 否   | 任务名称     |
| description   | string | 否   | 任务描述     |
| priority      | string | 否   | 优先级       |
| schedule_cron | string | 否   | Cron表达式   |

#### 响应

```json
// 200
{ "code": 0, "message": "更新成功", "data": { "id": "uuid" } }
```

---

### 5.5 DELETE /api/v1/tasks/{id} — 删除任务

**认证：** 需要 Bearer Token
**权限：** 仅 ADMIN

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 响应

```json
// 200
{ "code": 0, "message": "删除成功", "data": null }
```

**行为：** 软删除，仅 PENDING/SCHEDULED/COMPLETED 状态可删除。

---

### 5.6 POST /api/v1/tasks/{id}/start — 启动任务

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 响应

```json
// 200
{ "code": 0, "message": "任务已启动", "data": { "id": "uuid", "status": "RUNNING" } }
```

**行为：** 任务状态 PENDING → RUNNING，进入调度队列。

---

### 5.7 POST /api/v1/tasks/{id}/cancel — 取消任务

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 响应

```json
// 200
{ "code": 0, "message": "任务已取消", "data": { "id": "uuid", "status": "CANCELLED" } }
```

**行为：** 任务状态 → CANCELLED，已执行的用例结果保留。

---

### 5.8 GET /api/v1/tasks/{id}/logs — 任务日志

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(CRU), OPS(R)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 任务ID |

#### 查询参数

| 参数名    | 类型   | 必填 | 说明                    |
|----------|--------|------|------------------------|
| page     | int    | 否   | 页码                    |
| page_size| int    | 否   | 每页条数                 |
| level    | string | 否   | 日志级别：DEBUG/INFO/WARNING/ERROR |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "level": "INFO",
                "message": "用例[登录功能测试]执行成功",
                "case_id": "case-uuid",
                "created_at": "2026-05-12T10:00:05Z"
            }
        ],
        "total": 200,
        "page": 1,
        "page_size": 20
    }
}
```

---

## 6. 结果展示模块（RESULT）

### 6.1 GET /api/v1/results/overview — 结果概览

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), TESTER(R+E), OPS(R)

#### 查询参数

| 参数名   | 类型   | 必填 | 说明   |
|---------|--------|------|-------|
| task_id | string | 是   | 任务ID |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "task_id": "uuid",
        "total_cases": 20,
        "success_count": 15,
        "failed_count": 3,
        "skipped_count": 2,
        "success_rate": 75.0,
        "duration": 120.5
    }
}
```

---

### 6.2 GET /api/v1/results — 结果列表

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), TESTER(R+E), OPS(R)

#### 查询参数

| 参数名    | 类型   | 必填 | 说明                              |
|----------|--------|------|----------------------------------|
| task_id  | string | 是   | 任务ID                            |
| page     | int    | 否   | 页码                              |
| page_size| int    | 否   | 每页条数                           |
| status   | string | 否   | 状态筛选：SUCCESS/FAILED/SKIPPED/ERROR |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "case": { "id": "case-uuid", "name": "登录功能测试", "type": "UI" },
                "status": "SUCCESS",
                "duration_ms": 5200,
                "started_at": "2026-05-12T10:00:00Z",
                "completed_at": "2026-05-12T10:00:05Z"
            }
        ],
        "total": 20,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 6.3 GET /api/v1/results/api/{result_id} — 结果详情

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), TESTER(R+E), OPS(R)

#### 路径参数

| 参数名    | 类型   | 说明     |
|----------|--------|---------|
| result_id| string | 结果ID   |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "id": "uuid",
        "task_id": "task-uuid",
        "case": { "id": "case-uuid", "name": "登录功能测试", "type": "API" },
        "status": "FAILED",
        "duration_ms": 3200,
        "detail": {
            "request": {
                "method": "POST",
                "url": "/api/v1/auth/login",
                "headers": { "Content-Type": "application/json" },
                "body": { "username": "test", "password": "wrong" }
            },
            "response": {
                "status_code": 401,
                "body": { "code": "INVALID_CREDENTIALS", "message": "用户名或密码错误" },
                "time_ms": 150
            },
            "assertions": [
                { "type": "status_code", "expected": 200, "actual": 401, "passed": false }
            ]
        },
        "error_message": "断言失败：状态码不匹配",
        "screenshots": [],
        "video_path": null,
        "started_at": "2026-05-12T10:00:00Z",
        "completed_at": "2026-05-12T10:00:03Z"
    }
}
```

---

### 6.4 POST /api/v1/results/{task_id}/export — 结果导出

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), TESTER(R+E)

#### 路径参数

| 参数名  | 类型   | 说明   |
|--------|--------|-------|
| task_id| string | 任务ID |

#### 请求参数（Body）

| 参数名  | 类型   | 必填 | 说明                    |
|--------|--------|------|------------------------|
| format | string | 是   | 导出格式：EXCEL/PDF/HTML |

#### 响应

```json
// 200（文件下载）
Content-Type: application/octet-stream
Content-Disposition: attachment; filename=task_result_report.xlsx
```

---

### 6.5 POST /api/v1/results/{task_id}/share — 生成分享链接

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), TESTER(R+E)

#### 路径参数

| 参数名  | 类型   | 说明   |
|--------|--------|-------|
| task_id| string | 任务ID |

#### 请求参数（Body）

| 参数名      | 类型   | 必填 | 说明                   |
|------------|--------|------|-----------------------|
| expires_in | int    | 否   | 有效期(秒)，默认86400   |
| password   | string | 否   | 访问密码（可选）        |

#### 响应

```json
// 201
{
    "code": 0,
    "message": "分享链接已生成",
    "data": {
        "share_url": "http://{host}/api/v1/results/share/{token}",
        "token": "share-token-string",
        "expires_at": "2026-05-13T10:00:00Z"
    }
}
```

---

### 6.6 GET /api/v1/results/share/{token} — 访问分享链接

**认证：** 无需
**权限：** 无

#### 路径参数

| 参数名 | 类型   | 说明        |
|-------|--------|------------|
| token | string | 分享Token   |

#### 查询参数

| 参数名   | 类型   | 必填 | 说明             |
|---------|--------|------|-----------------|
| password| string | 否   | 访问密码（如设置了密码） |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "task": {
            "name": "回归测试-登录模块",
            "status": "SUCCESS",
            "total_cases": 20,
            "success_count": 18,
            "failed_count": 2
        },
        "results": [ ... ]
    }
}
```

**错误场景：**

| 场景 | 错误码 | HTTP |
|------|--------|------|
| Token不存在 | SHARE_NOT_FOUND | 404 |
| 链接已过期 | SHARE_EXPIRED | 410 |
| 需要密码 | SHARE_PASSWORD_REQUIRED | 401 |
| 密码错误 | SHARE_PASSWORD_INVALID | 401 |

---

## 7. 节点管理模块（NODE）

### 7.1 GET /api/v1/nodes — 节点列表

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(R), OPS(CRUD)

#### 查询参数

| 参数名    | 类型   | 必填 | 说明                              |
|----------|--------|------|----------------------------------|
| page     | int    | 否   | 页码                              |
| page_size| int    | 否   | 每页条数                           |
| status   | string | 否   | 状态筛选：ONLINE/OFFLINE/BUSY/DISABLED |
| keyword  | string | 否   | 节点名称模糊搜索                    |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "name": "Node-01",
                "host": "192.168.1.101",
                "port": 8080,
                "status": "ONLINE",
                "group": { "id": "uuid", "name": "UI测试组" },
                "max_concurrent": 5,
                "cpu_usage": 45.2,
                "memory_usage": 62.8,
                "disk_usage": 35.0,
                "current_tasks": 2,
                "is_enabled": true,
                "last_heartbeat_at": "2026-05-12T10:00:30Z",
                "created_at": "2026-05-01T10:00:00Z"
            }
        ],
        "total": 10,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 7.2 POST /api/v1/nodes — 节点注册

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), OPS(CRUD)

#### 请求参数（Body）

| 参数名          | 类型   | 必填 | 说明               |
|----------------|--------|------|--------------------|
| name           | string | 是   | 节点名称            |
| host           | string | 是   | 主机地址            |
| port           | int    | 是   | 端口号              |
| group_id       | string | 否   | 所属分组ID          |
| max_concurrent | int    | 否   | 最大并发数，默认5    |

#### 响应

```json
// 201
{ "code": 0, "message": "注册成功", "data": { "id": "uuid" } }
```

**行为：** 手动录入节点，初始状态为 OFFLINE，等待客户端连接。

---

### 7.3 GET /api/v1/nodes/{id} — 节点详情

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(R), OPS(CRUD)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 节点ID |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "id": "uuid",
        "name": "Node-01",
        "host": "192.168.1.101",
        "port": 8080,
        "status": "ONLINE",
        "group": { "id": "uuid", "name": "UI测试组" },
        "max_concurrent": 5,
        "cpu_usage": 45.2,
        "memory_usage": 62.8,
        "disk_usage": 35.0,
        "current_tasks": 2,
        "is_enabled": true,
        "last_heartbeat_at": "2026-05-12T10:00:30Z",
        "recent_tasks": [
            { "id": "task-uuid", "name": "回归测试", "status": "RUNNING" }
        ],
        "created_at": "2026-05-01T10:00:00Z",
        "updated_at": "2026-05-12T10:00:30Z"
    }
}
```

---

### 7.4 PUT /api/v1/nodes/{id} — 更新节点

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), OPS(CRUD)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 节点ID |

#### 请求参数（Body）

| 参数名          | 类型    | 必填 | 说明           |
|----------------|---------|------|---------------|
| name           | string  | 否   | 节点名称       |
| group_id       | string  | 否   | 所属分组ID     |
| max_concurrent | int     | 否   | 最大并发数     |
| is_enabled     | boolean | 否   | 是否启用       |

#### 响应

```json
// 200
{ "code": 0, "message": "更新成功", "data": { "id": "uuid" } }
```

**行为：** 禁用节点后不再分配新任务，已有任务继续完成。

---

### 7.5 DELETE /api/v1/nodes/{id} — 删除节点

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), OPS(CRUD)

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 节点ID |

#### 响应

```json
// 200
{ "code": 0, "message": "删除成功", "data": null }
```

**行为：** 仅 OFFLINE 或 DISABLED 状态的节点可删除。

---

### 7.6 POST /api/v1/nodes/{id}/heartbeat — 节点心跳

**认证：** 需要 Bearer Token（节点专用Token）
**权限：** 节点客户端

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 节点ID |

#### 请求参数（Body）

| 参数名       | 类型  | 必填 | 说明          |
|-------------|-------|------|--------------|
| cpu_usage   | float | 是   | CPU使用率(%)  |
| memory_usage| float | 是   | 内存使用率(%) |
| disk_usage  | float | 是   | 磁盘使用率(%) |
| current_tasks| int  | 是   | 当前任务数    |

#### 响应

```json
// 200
{ "code": 0, "message": "success", "data": { "status": "ONLINE" } }
```

**行为：** 客户端每30秒上报心跳，服务端更新 last_heartbeat_at 和资源指标。超过90秒未收到心跳 → 标记为 OFFLINE。

---

### 7.7 GET /api/v1/nodes/groups — 节点分组列表

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), TESTER(R), OPS(CRUD)

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "name": "UI测试组",
                "description": "负责UI自动化测试",
                "node_count": 3,
                "online_count": 2,
                "created_at": "2026-05-01T10:00:00Z"
            }
        ],
        "total": 3,
        "page": 1,
        "page_size": 20
    }
}
```

---

## 8. 系统管理模块（SYS）

### 8.1 GET /api/v1/system/logs — 操作日志

**认证：** 需要 Bearer Token
**权限：** ADMIN(R+E), OPS(R)

#### 查询参数

| 参数名         | 类型   | 必填 | 说明                              |
|---------------|--------|------|----------------------------------|
| page          | int    | 否   | 页码                              |
| page_size     | int    | 否   | 每页条数                           |
| operation     | string | 否   | 操作类型：CREATE/UPDATE/DELETE/LOGIN/LOGOUT/EXPORT |
| resource_type | string | 否   | 资源类型：USER/CASE/TASK/RESULT/NODE/SYSTEM |
| start_time    | string | 否   | 开始时间（ISO 8601）               |
| end_time      | string | 否   | 结束时间（ISO 8601）               |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "user": { "id": "uuid", "username": "admin" },
                "operation": "CREATE",
                "resource_type": "CASE",
                "resource_id": "case-uuid",
                "description": "创建测试用例[登录功能测试]",
                "ip": "192.168.1.100",
                "created_at": "2026-05-12T10:00:00Z"
            }
        ],
        "total": 500,
        "page": 1,
        "page_size": 20
    }
}
```

---

### 8.2 GET /api/v1/system/notifications — 通知列表

**认证：** 需要 Bearer Token
**权限：** 所有角色（仅查看自己的通知）

#### 查询参数

| 参数名    | 类型    | 必填 | 说明                    |
|----------|---------|------|------------------------|
| page     | int     | 否   | 页码                    |
| page_size| int     | 否   | 每页条数                 |
| is_read  | boolean | 否   | 是否已读筛选             |

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "list": [
            {
                "id": "uuid",
                "title": "任务执行完成",
                "content": "任务[回归测试-登录模块]已执行完成，成功率95%",
                "type": "TASK_COMPLETE",
                "is_read": false,
                "created_at": "2026-05-12T10:05:00Z"
            }
        ],
        "total": 30,
        "page": 1,
        "page_size": 20,
        "unread_count": 5
    }
}
```

---

### 8.3 PUT /api/v1/system/notifications/{id}/read — 标记已读

**认证：** 需要 Bearer Token
**权限：** 所有角色

#### 路径参数

| 参数名 | 类型   | 说明   |
|-------|--------|-------|
| id    | string | 通知ID |

#### 响应

```json
// 200
{ "code": 0, "message": "success", "data": null }
```

**行为：** 设置 is_read=true，read_at=当前时间。

---

### 8.4 GET /api/v1/system/config — 获取配置

**认证：** 需要 Bearer Token
**权限：** ADMIN(CRUD), OPS(R)

#### 响应

```json
// 200
{
    "code": 0,
    "message": "success",
    "data": {
        "configs": [
            {
                "key": "login_max_fail_count",
                "value": "5",
                "description": "登录失败最大次数"
            },
            {
                "key": "token_expire_hours",
                "value": "24",
                "description": "Token有效期(小时)"
            }
        ]
    }
}
```

---

### 8.5 PUT /api/v1/system/config — 更新配置

**认证：** 需要 Bearer Token
**权限：** 仅 ADMIN

#### 请求参数（Body）

| 参数名   | 类型     | 必填 | 说明       |
|---------|----------|------|-----------|
| configs | object[] | 是   | 配置项列表 |
| configs[].key   | string | 是 | 配置键    |
| configs[].value | string | 是 | 配置值    |

#### 响应

```json
// 200
{ "code": 0, "message": "配置已更新", "data": null }
```

---

### 8.6 GET /health — 健康检查

**认证：** 无需
**权限：** 无

#### 响应

```json
// 200
{ "status": "ok", "timestamp": "2026-05-12T10:00:00Z" }
```

**行为：** 无需认证，返回服务基本状态。

---

### 8.7 GET /ready — 就绪检查

**认证：** 无需
**权限：** 无

#### 响应

```json
// 200
{
    "status": "ready",
    "checks": {
        "database": "ok",
        "redis": "ok"
    },
    "timestamp": "2026-05-12T10:00:00Z"
}
```

**行为：** 检查数据库和 Redis 连接状态，全部正常返回 ready。

---

## 9. 附录

### 9.1 API 汇总

| 模块 | API数量 | 核心接口 |
|------|--------|---------|
| 认证 (AUTH) | 7 | login, logout, refresh-token, me, forgot/verify/reset-password |
| 用例 (CASE) | 8 | CRUD, import, export, versions, rollback |
| 任务 (TASK) | 8 | CRUD, start, cancel, logs |
| 结果 (RESULT) | 6 | overview, list, detail, export, share, share-access |
| 节点 (NODE) | 7 | CRUD, heartbeat, groups |
| 系统 (SYS) | 7 | logs, notifications, config, health, ready |
| **合计** | **43** | |

### 9.2 状态码使用规范

| HTTP状态码 | 使用场景 |
|-----------|---------|
| 200 | 成功（GET/PUT/PATCH） |
| 201 | 创建成功（POST） |
| 400 | 请求格式错误 |
| 401 | 未认证或认证失效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 410 | 资源已过期 |
| 422 | 参数校验失败 |
| 423 | 账号锁定 |
| 500 | 服务器内部错误 |
