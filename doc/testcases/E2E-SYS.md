# E2E 验收测试用例 — SYS 系统管理模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-SYS-001 ~ FR-SYS-004

---

## 1. 操作日志（FR-SYS-001）

### TC-SYS-001 查看操作日志列表

**Given** 平台中已有操作日志记录
**When** 调用 `GET /api/v1/system/logs`
**Then**
- 返回 HTTP 200
- 分页日志列表，每条记录包含：`user_id`、`operation`、`resource_type`、`resource_id`、`description`、`ip`、`created_at`
- 按时间倒序排列

### TC-SYS-002 按操作类型筛选日志

**Given** 平台中存在 LOGIN、CREATE、DELETE 等操作类型的日志
**When** 调用 `GET /api/v1/system/logs?operation=LOGIN`
**Then**
- 仅返回 operation=LOGIN 的日志

### TC-SYS-003 按资源类型筛选日志

**Given** 平台中存在 USER、CASE、TASK 等资源类型的日志
**When** 调用 `GET /api/v1/system/logs?resource_type=CASE`
**Then**
- 仅返回 resource_type=CASE 的日志

### TC-SYS-004 日志自动记录 — 登录操作

**Given** 用户 `tester01` 执行登录操作
**When** 登录成功
**Then**
- `system_logs` 表新增一条记录
- `operation=LOGIN`
- `resource_type=USER`
- `description` 包含登录结果
- `ip` 为客户端 IP

### TC-SYS-005 日志自动记录 — 创建用例

**Given** 用户 `tester01` 创建了一条用例
**When** 创建成功
**Then**
- `system_logs` 表新增一条记录
- `operation=CREATE`
- `resource_type=CASE`
- `resource_id` 为新用例 ID

### TC-SYS-006 日志自动记录 — 删除操作

**Given** 管理员删除了一条用例
**When** 删除成功
**Then**
- `system_logs` 表新增一条记录
- `operation=DELETE`
- `resource_type=CASE`

### TC-SYS-007 OPS 角色查看日志

**Given** 用户 `ops01` 角色为 OPS，已登录
**When** 调用 `GET /api/v1/system/logs`
**Then**
- 返回 HTTP 200
- 可查看日志列表

### TC-SYS-008 TESTER 角色无权查看日志

**Given** 用户 `tester01` 角色为 TESTER，已登录
**When** 调用 `GET /api/v1/system/logs`
**Then**
- 返回 HTTP 403
- 错误码 `FORBIDDEN`

---

## 2. 消息通知（FR-SYS-002）

### TC-SYS-009 查看通知列表

**Given** 用户 `tester01` 有 3 条未读通知
**When** 调用 `GET /api/v1/system/notifications`
**Then**
- 返回 HTTP 200
- 列表包含 3 条通知
- 每条包含：`title`、`content`、`is_read`、`created_at`
- 按时间倒序排列

### TC-SYS-010 标记通知已读

**Given** 用户有一条未读通知 `notification_id=1`
**When** 调用 `PUT /api/v1/system/notifications/1/read`
**Then**
- 返回 HTTP 200
- 通知的 `is_read` 变为 `true`
- `read_at` 被设置为当前时间

### TC-SYS-011 任务完成触发通知

**Given** 用户 `tester01` 创建的任务 `task_id=100` 执行完成
**When** 任务状态变为 SUCCESS
**Then**
- `notifications` 表新增一条通知
- `user_id` 为 `tester01`
- `title` 包含任务名称和执行结果
- `content` 包含成功/失败用例数

### TC-SYS-012 节点离线触发通知

**Given** 节点 `node_id=1` 超过 90 秒未发送心跳
**When** 系统将节点标记为 OFFLINE
**Then**
- 运维人员和管理员收到通知
- 通知内容包含节点名称和离线时间

### TC-SYS-013 标记不存在的通知

**Given** 不存在 `notification_id=99999`
**When** 调用 `PUT /api/v1/system/notifications/99999/read`
**Then**
- 返回 HTTP 404

---

## 3. 系统配置（FR-SYS-003）

### TC-SYS-014 查看系统配置

**Given** 管理员已登录
**When** 调用 `GET /api/v1/system/config`
**Then**
- 返回 HTTP 200
- 返回配置项列表，包含：
  - `login_max_attempts`（登录失败限制）
  - `lock_duration_minutes`（锁定时长）
  - `token_expire_hours`（Token 有效期）
  - `heartbeat_interval_seconds`（心跳间隔）
  - `log_retention_days`（日志保留天数）
- 每项包含 `key`、`value`、`description`

### TC-SYS-015 修改系统配置

**Given** 管理员已登录
**When** 调用 `PUT /api/v1/system/config`，请求体：
```json
{
  "login_max_attempts": "10",
  "lock_duration_minutes": "30"
}
```
**Then**
- 返回 HTTP 200
- 配置项更新成功
- 部分配置页面提示"需重启生效"

### TC-SYS-016 TESTER 无权修改配置

**Given** 用户 `tester01` 角色为 TESTER
**When** 调用 `PUT /api/v1/system/config`
**Then**
- 返回 HTTP 403
- 错误码 `FORBIDDEN`

### TC-SYS-017 OPS 查看配置（只读）

**Given** 用户 `ops01` 角色为 OPS
**When** 调用 `GET /api/v1/system/config`
**Then**
- 返回 HTTP 200
- 可查看配置

**When** 调用 `PUT /api/v1/system/config`
**Then**
- 返回 HTTP 403，错误码 `FORBIDDEN`

---

## 4. 健康检查（FR-SYS-004）

### TC-SYS-018 健康检查 — 正常

**Given** 平台服务正常运行
**When** 调用 `GET /health`（无需认证）
**Then**
- 返回 HTTP 200
- 响应体包含服务状态 `status=healthy`
- 包含数据库连接状态
- 包含 Redis 连接状态

### TC-SYS-019 就绪检查 — 正常

**Given** 平台服务正常运行，数据库和 Redis 可用
**When** 调用 `GET /ready`（无需认证）
**Then**
- 返回 HTTP 200
- 响应体 `status=ready`

### TC-SYS-020 健康检查 — 数据库不可用

**Given** PostgreSQL 服务不可用
**When** 调用 `GET /health`
**Then**
- 返回 HTTP 503
- `status=unhealthy`
- 数据库连接状态为 `disconnected`

### TC-SYS-021 就绪检查 — 服务未就绪

**Given** 平台正在启动中，数据库连接未建立
**When** 调用 `GET /ready`
**Then**
- 返回 HTTP 503
- `status=not_ready`

---

## 5. 系统统计

### TC-SYS-022 查看系统统计数据

**Given** 平台运行中，有用户、用例、任务、节点数据
**When** 调用 `GET /api/v1/system/stats`
**Then**
- 返回 HTTP 200
- 包含：总用户数、总用例数、总任务数、在线节点数、今日执行任务数
