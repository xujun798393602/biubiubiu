# E2E 验收测试用例 — TASK 任务管理模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-TASK-001 ~ FR-TASK-004

---

## 1. 创建任务（FR-TASK-001）

### TC-TASK-001 立即执行任务

**Given** 平台中存在 3 条 ACTIVE 状态的用例（id=1,2,3），当前用户角色为 TESTER
**When** 调用 `POST /api/v1/tasks`，请求体：
```json
{
  "name": "登录模块回归测试",
  "description": "验证登录相关功能",
  "priority": "HIGH",
  "case_ids": [1, 2, 3],
  "execute_type": "IMMEDIATE"
}
```
**Then**
- 返回 HTTP 201
- 响应体包含新任务 `id`
- 任务状态为 `PENDING`
- `total_cases=3`
- 数据库 `task_cases` 表新增 3 条关联记录
- 任务进入调度队列

### TC-TASK-002 定时执行任务

**Given** 平台中存在用例，当前用户已登录
**When** 调用 `POST /api/v1/tasks`，请求体：
```json
{
  "name": "每日凌晨回归测试",
  "priority": "MEDIUM",
  "case_ids": [1, 2],
  "execute_type": "SCHEDULED",
  "schedule_cron": "0 2 * * *"
}
```
**Then**
- 返回 HTTP 201
- 任务状态为 `SCHEDULED`
- 数据库记录 `schedule_cron="0 2 * * *"`
- 响应体包含 `next_run_time`（下次执行时间）

### TC-TASK-003 创建任务 — 空用例列表

**Given** 用户已登录
**When** 调用 `POST /api/v1/tasks`，请求体 `case_ids` 为空数组 `[]`
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"至少选择一个用例"

### TC-TASK-004 创建任务 — 用例超过100个

**Given** 用户已登录，平台中存在 101 条用例
**When** 调用 `POST /api/v1/tasks`，`case_ids` 包含 101 个 ID
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"单任务最多100个用例"

### TC-TASK-005 创建任务 — 用例不存在

**Given** 用户已登录
**When** 调用 `POST /api/v1/tasks`，`case_ids` 包含不存在的 ID `[99999]`
**Then**
- 返回 HTTP 404
- 错误码 `CASE_NOT_FOUND`
- 任务不被创建

### TC-TASK-006 创建任务 — 名称为空

**Given** 用户已登录
**When** 调用 `POST /api/v1/tasks`，`name` 为空字符串
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`

### TC-TASK-007 创建任务 — 优先级默认值

**Given** 用户已登录
**When** 调用 `POST /api/v1/tasks`，不传 `priority` 字段
**Then**
- 返回 HTTP 201
- `priority` 默认为 `MEDIUM`

---

## 2. 任务调度（FR-TASK-002）

### TC-TASK-008 按优先级调度

**Given** 调度队列中有 3 个待执行任务：优先级 HIGH、MEDIUM、LOW
**When** 调度器执行调度
**Then**
- HIGH 优先级任务最先被调度
- 其次是 MEDIUM
- 最后是 LOW

### TC-TASK-009 负载均衡分配

**Given** 有 2 个在线节点：Node-01 CPU 使用率 30%，Node-02 CPU 使用率 70%
**When** 调度器分配任务
**Then**
- 任务分配到 Node-01（负载更低的节点）

### TC-TASK-010 节点并发上限检查

**Given** Node-01 的 `max_concurrent=5`，当前已执行 5 个任务
**When** 新任务需要调度
**Then**
- 新任务不分配到 Node-01
- 分配到其他有空闲容量的节点

### TC-TASK-011 无可用节点

**Given** 所有节点均为 OFFLINE 或 DISABLED 状态
**When** 有新任务需要调度
**Then**
- 任务保持 PENDING 状态
- 不被分配到任何节点
- 任务日志记录"无可用节点"

---

## 3. 任务状态管理（FR-TASK-003）

### TC-TASK-012 启动待执行任务

**Given** 任务 `task_id=100` 状态为 PENDING
**When** 调用 `POST /api/v1/tasks/100/start`
**Then**
- 返回 HTTP 200
- 任务状态变为 `RUNNING`
- `started_at` 被设置

### TC-TASK-013 取消执行中任务

**Given** 任务 `task_id=100` 状态为 RUNNING
**When** 调用 `POST /api/v1/tasks/100/cancel`
**Then**
- 返回 HTTP 200
- 任务状态变为 `CANCELLED`
- 已执行的用例结果保留
- `finished_at` 被设置

### TC-TASK-014 取消待执行任务

**Given** 任务 `task_id=100` 状态为 PENDING
**When** 调用 `POST /api/v1/tasks/100/cancel`
**Then**
- 返回 HTTP 200
- 任务状态变为 `CANCELLED`

### TC-TASK-015 任务自动完成

**Given** 任务 `task_id=100` 状态为 RUNNING，包含 3 个用例
**When** 3 个用例全部执行完成
**Then**
- 任务状态自动变为 `SUCCESS`
- `finished_at` 被设置
- `success_count`、`failed_count` 统计正确

### TC-TASK-016 任务自动失败

**Given** 任务 `task_id=100` 状态为 RUNNING
**When** 执行过程中发生不可恢复的错误
**Then**
- 任务状态变为 `FAILED`
- 错误信息记录在任务日志中

### TC-TASK-017 启动非 PENDING 状态任务

**Given** 任务 `task_id=100` 状态为 SUCCESS
**When** 调用 `POST /api/v1/tasks/100/start`
**Then**
- 返回 HTTP 400
- 提示"只有待执行状态的任务可以启动"

### TC-TASK-018 取消已完成任务

**Given** 任务 `task_id=100` 状态为 SUCCESS
**When** 调用 `POST /api/v1/tasks/100/cancel`
**Then**
- 返回 HTTP 400
- 提示"已完成的任务无法取消"

### TC-TASK-019 操作不存在的任务

**Given** 不存在 `task_id=99999`
**When** 调用 `POST /api/v1/tasks/99999/start`
**Then**
- 返回 HTTP 404
- 错误码 `TASK_NOT_FOUND`

---

## 4. 任务日志（FR-TASK-004）

### TC-TASK-020 查看任务执行日志

**Given** 任务 `task_id=100` 已执行完成，执行过程中产生了日志
**When** 调用 `GET /api/v1/tasks/100/logs`
**Then**
- 返回 HTTP 200
- 日志列表按时间正序排列
- 每条日志包含：`timestamp`、`level`（INFO/WARNING/ERROR）、`message`
- 包含用例执行开始、执行结束、断言结果等信息

### TC-TASK-021 任务日志 — 按级别筛选

**Given** 任务执行日志中包含 INFO、WARNING、ERROR 级别日志
**When** 调用 `GET /api/v1/tasks/100/logs?level=ERROR`
**Then**
- 仅返回 ERROR 级别的日志

### TC-TASK-022 查看不存在任务的日志

**Given** 不存在 `task_id=99999`
**When** 调用 `GET /api/v1/tasks/99999/logs`
**Then**
- 返回 HTTP 404
- 错误码 `TASK_NOT_FOUND`

---

## 5. 任务列表与筛选

### TC-TASK-023 查看任务列表

**Given** 平台中存在多个任务
**When** 调用 `GET /api/v1/tasks`
**Then**
- 返回 HTTP 200
- 分页任务列表，包含：`name`、`status`、`priority`、`total_cases`、`success_count`、`failed_count`、`created_at`
- 按创建时间倒序排列

### TC-TASK-024 按状态筛选任务

**Given** 平台中存在不同状态的任务
**When** 调用 `GET /api/v1/tasks?status=RUNNING`
**Then**
- 仅返回状态为 RUNNING 的任务

### TC-TASK-025 按优先级筛选任务

**Given** 平台中存在不同优先级的任务
**When** 调用 `GET /api/v1/tasks?priority=HIGH`
**Then**
- 仅返回优先级为 HIGH 的任务
