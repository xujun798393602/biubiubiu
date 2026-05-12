# E2E 验收测试用例 — CASE 用例管理模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-CASE-001 ~ FR-CASE-006

---

## 1. 用例列表查询（FR-CASE-001）

### TC-CASE-001 无条件查询全部用例

**Given** 平台中已存在 10 条用例，包含 UI/API/PERFORMANCE 三种类型
**When** 调用 `GET /api/v1/cases`
**Then**
- 返回 HTTP 200
- 返回分页列表，`total=10`
- 用例按创建时间倒序排列
- 每条记录包含 `id`、`name`、`type`、`status`、`priority`、`created_at`

### TC-CASE-002 按类型筛选

**Given** 平台中存在 UI 用例 3 条、API 用例 5 条、PERFORMANCE 用例 2 条
**When** 调用 `GET /api/v1/cases?type=API`
**Then**
- 返回 HTTP 200
- 列表仅包含 type=API 的用例
- `total=5`

### TC-CASE-003 按关键词模糊搜索

**Given** 平台中存在用例名为"登录功能测试"、"登录异常测试"、"注册功能测试"
**When** 调用 `GET /api/v1/cases?keyword=登录`
**Then**
- 返回 HTTP 200
- 列表包含"登录功能测试"和"登录异常测试"
- 不包含"注册功能测试"
- `total=2`

### TC-CASE-004 组合筛选

**Given** 平台中存在多条用例
**When** 调用 `GET /api/v1/cases?type=UI&priority=P1`
**Then**
- 返回 HTTP 200
- 仅返回同时满足 type=UI 且 priority=P1 的用例

### TC-CASE-005 分页查询

**Given** 平台中存在 25 条用例
**When** 调用 `GET /api/v1/cases?page=2&pageSize=10`
**Then**
- 返回 HTTP 200
- 列表包含第 11~20 条记录
- `total=25`，`page=2`，`pageSize=10`

### TC-CASE-006 空结果查询

**Given** 平台中不存在 type=APP 的用例
**When** 调用 `GET /api/v1/cases?type=APP`
**Then**
- 返回 HTTP 200
- 列表为空 `[]`
- `total=0`

---

## 2. 创建用例（FR-CASE-002）

### TC-CASE-007 创建 UI 测试用例

**Given** 用户已登录，角色为 TESTER
**When** 调用 `POST /api/v1/cases`，请求体：
```json
{
  "name": "登录页面UI测试",
  "type": "UI",
  "priority": "P1",
  "status": "ACTIVE",
  "module": "认证模块",
  "tags": ["登录", "UI"],
  "description": "验证登录页面的UI交互",
  "preconditions": "用户已注册",
  "ui_url": "http://example.com/login",
  "ui_script": "async def test_login(page): ...",
  "ui_script_type": "MANUAL"
}
```
**Then**
- 返回 HTTP 201
- 响应体包含新用例 `id`
- 数据库中用例记录完整保存
- `version=1`

### TC-CASE-008 创建接口测试用例

**Given** 用户已登录，角色为 TESTER
**When** 调用 `POST /api/v1/cases`，请求体包含 API 类型字段：
```json
{
  "name": "登录接口测试",
  "type": "API",
  "priority": "P0",
  "api_url": "http://example.com/api/v1/auth/login",
  "api_method": "POST",
  "api_headers": {"Content-Type": "application/json"},
  "api_body_type": "JSON",
  "api_body": "{\"username\":\"test\",\"password\":\"123456\"}",
  "api_timeout": 30000,
  "api_assertions": [
    {"type": "status_code", "expected": 200},
    {"type": "jsonpath", "path": "$.code", "expected": 0}
  ]
}
```
**Then**
- 返回 HTTP 201
- 用例类型为 API
- 断言规则正确保存

### TC-CASE-009 创建性能压测用例

**Given** 用户已登录，角色为 TESTER
**When** 调用 `POST /api/v1/cases`，请求体包含 PERFORMANCE 类型字段：
```json
{
  "name": "登录接口压测",
  "type": "PERFORMANCE",
  "priority": "P1",
  "perf_url": "http://example.com/api/v1/auth/login",
  "perf_vusers": 100,
  "perf_spawn_rate": 10,
  "perf_duration": 60,
  "perf_assertions": [
    {"type": "p95_response_time", "max": 500},
    {"type": "error_rate", "max": 0.01}
  ]
}
```
**Then**
- 返回 HTTP 201
- 用例类型为 PERFORMANCE
- 性能参数正确保存

### TC-CASE-010 创建用例 — 名称为空

**Given** 用户已登录
**When** 调用 `POST /api/v1/cases`，请求体中 `name` 为空字符串
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"用例名称不能为空"

### TC-CASE-011 创建用例 — 类型无效

**Given** 用户已登录
**When** 调用 `POST /api/v1/cases`，请求体中 `type` 为 `INVALID_TYPE`
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示类型必须为 UI/API/PERFORMANCE

### TC-CASE-012 创建用例 — 默认值

**Given** 用户已登录
**When** 调用 `POST /api/v1/cases`，仅传必填字段 `name` 和 `type`
**Then**
- 返回 HTTP 201
- `priority` 默认为 `P2`
- `status` 默认为 `DRAFT`
- `version` 为 `1`

---

## 3. 更新用例（FR-CASE-003）

### TC-CASE-013 正常更新用例

**Given** 已存在用例 `case_id=100`，`version=1`
**When** 调用 `PUT /api/v1/cases/100`，请求体：
```json
{
  "name": "更新后的用例名称",
  "priority": "P0"
}
```
**Then**
- 返回 HTTP 200
- `name` 和 `priority` 字段更新成功
- `version` 自动递增为 `2`
- 其他字段不变

### TC-CASE-014 更新不存在的用例

**Given** 不存在 `case_id=99999`
**When** 调用 `PUT /api/v1/cases/99999`
**Then**
- 返回 HTTP 404
- 错误码 `CASE_NOT_FOUND`

### TC-CASE-015 更新用例 — 只更新部分字段

**Given** 已存在用例 `case_id=100`，`name="原名称"`，`priority=P1`
**When** 调用 `PUT /api/v1/cases/100`，仅传 `{"name": "新名称"}`
**Then**
- 返回 HTTP 200
- `name` 更新为"新名称"
- `priority` 保持 `P1` 不变

---

## 4. 删除用例（FR-CASE-004）

### TC-CASE-016 ADMIN 删除用例

**Given** 已存在用例 `case_id=100`，当前用户角色为 ADMIN
**When** 调用 `DELETE /api/v1/cases/100`
**Then**
- 返回 HTTP 200
- 数据库中 `deleted_at` 被设置（软删除）
- 查询列表时不再显示该用例

### TC-CASE-017 TESTER 无权删除用例

**Given** 已存在用例 `case_id=100`，当前用户角色为 TESTER
**When** 调用 `DELETE /api/v1/cases/100`
**Then**
- 返回 HTTP 403
- 错误码 `FORBIDDEN`
- 用例未被删除

### TC-CASE-018 删除不存在的用例

**Given** 不存在 `case_id=99999`
**When** 调用 `DELETE /api/v1/cases/99999`
**Then**
- 返回 HTTP 404
- 错误码 `CASE_NOT_FOUND`

---

## 5. 用例导入导出（FR-CASE-005）

### TC-CASE-019 导出用例为 Excel

**Given** 平台中存在 5 条用例
**When** 调用 `POST /api/v1/cases/export`，请求体：
```json
{
  "format": "xlsx",
  "case_ids": [1, 2, 3, 4, 5]
}
```
**Then**
- 返回 HTTP 200
- Content-Type 为 `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`
- 文件包含 5 条用例的完整信息
- 表头包含：名称、类型、优先级、状态、描述等

### TC-CASE-020 导出用例为 JSON

**Given** 平台中存在用例
**When** 调用 `POST /api/v1/cases/export`，请求体 `format=json`
**Then**
- 返回 HTTP 200
- Content-Type 为 `application/json`
- 返回 JSON 数组，每条用例包含所有字段

### TC-CASE-021 导入用例

**Given** 用户准备了包含 3 条用例的 JSON 文件
**When** 调用 `POST /api/v1/cases/import`，上传文件
**Then**
- 返回 HTTP 200
- 响应体包含导入结果：成功 3 条，失败 0 条
- 数据库中新增 3 条用例记录
- 每条用例的 `status` 默认为 `DRAFT`

### TC-CASE-022 导入用例 — 格式错误

**Given** 用户准备了格式错误的 JSON 文件（缺少必填字段）
**When** 调用 `POST /api/v1/cases/import`
**Then**
- 返回 HTTP 422
- 提示具体的格式错误信息
- 不创建任何用例

---

## 6. 用例版本管理（FR-CASE-006）

### TC-CASE-023 查看用例版本历史

**Given** 用例 `case_id=100` 已被修改 3 次，当前 `version=3`
**When** 调用 `GET /api/v1/cases/100/versions`
**Then**
- 返回 HTTP 200
- 列表包含 3 个版本记录
- 每条记录包含：版本号、修改时间、修改人、变更内容摘要

### TC-CASE-024 回滚到历史版本

**Given** 用例 `case_id=100` 当前 `version=3`，要回滚到 `version=1`
**When** 调用 `POST /api/v1/cases/100/rollback`，请求体 `{"version": 1}`
**Then**
- 返回 HTTP 200
- 用例内容恢复到 version=1 时的状态
- 当前版本号递增为 `4`
- 版本历史新增一条回滚记录

### TC-CASE-025 回滚 — 版本号不存在

**Given** 用例 `case_id=100` 历史版本为 1、2、3
**When** 调用 `POST /api/v1/cases/100/rollback`，请求体 `{"version": 99}`
**Then**
- 返回 HTTP 404
- 提示"版本不存在"
