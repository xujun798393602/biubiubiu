# E2E 验收测试用例 — NODE 节点管理模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-NODE-001 ~ FR-NODE-005

---

## 1. 节点注册（FR-NODE-001）

### TC-NODE-001 客户端自动注册

**Given** 运维人员已部署节点容器，容器内运行 node-agent
**When** 节点容器启动，agent 向平台发送注册请求
**Then**
- 平台自动创建节点记录
- 节点状态为 `ONLINE`
- 记录节点信息：名称、IP、端口、系统信息、CPU/内存/磁盘
- 节点出现在节点列表中

### TC-NODE-002 手动录入节点

**Given** 管理员已登录
**When** 调用 `POST /api/v1/nodes`，请求体：
```json
{
  "name": "Node-03",
  "host": "192.168.1.103",
  "port": 8080,
  "group_id": 1,
  "max_concurrent": 5
}
```
**Then**
- 返回 HTTP 201
- 响应体包含新节点 `id`
- 节点状态为 `OFFLINE`（等待客户端连接）
- `max_concurrent=5`

### TC-NODE-003 手动录入 — 名称重复

**Given** 已存在节点 `name="Node-01"`
**When** 调用 `POST /api/v1/nodes`，`name` 为 `"Node-01"`
**Then**
- 返回 HTTP 409
- 提示"节点名称已存在"

### TC-NODE-004 手动录入 — 参数校验

**Given** 管理员已登录
**When** 调用 `POST /api/v1/nodes`，缺少必填字段 `host`
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"主机地址不能为空"

---

## 2. 节点列表（FR-NODE-002）

### TC-NODE-005 查看节点列表

**Given** 平台中已注册 5 个节点，状态各异
**When** 调用 `GET /api/v1/nodes`
**Then**
- 返回 HTTP 200
- 分页列表，每条记录包含：`name`、`host`、`port`、`status`、`cpu_usage`、`memory_usage`、`disk_usage`、`current_tasks`、`last_heartbeat_at`

### TC-NODE-006 按状态筛选

**Given** 平台中存在 ONLINE 和 OFFLINE 节点
**When** 调用 `GET /api/v1/nodes?status=ONLINE`
**Then**
- 仅返回状态为 ONLINE 的节点

### TC-NODE-007 按关键词搜索

**Given** 平台中存在节点 "Node-01"、"Node-02"、"Worker-01"
**When** 调用 `GET /api/v1/nodes?keyword=Node`
**Then**
- 返回 "Node-01" 和 "Node-02"
- 不包含 "Worker-01"

### TC-NODE-008 节点列表分页

**Given** 平台中存在 15 个节点
**When** 调用 `GET /api/v1/nodes?page=1&pageSize=10`
**Then**
- 返回前 10 个节点
- `total=15`

---

## 3. 节点心跳（FR-NODE-003）

### TC-NODE-009 正常心跳上报

**Given** 节点 `node_id=1` 状态为 ONLINE
**When** 节点调用 `POST /api/v1/nodes/1/heartbeat`，请求体：
```json
{
  "cpu_usage": 45.2,
  "memory_usage": 60.5,
  "disk_usage": 30.0,
  "current_tasks": 2
}
```
**Then**
- 返回 HTTP 200
- 数据库中节点的 `cpu_usage`、`memory_usage`、`disk_usage` 更新
- `last_heartbeat_at` 更新为当前时间

### TC-NODE-010 节点离线判定

**Given** 节点 `node_id=1` 最后一次心跳时间为 100 秒前
**When** 后台检测任务执行
**Then**
- 节点状态变为 `OFFLINE`
- 不再分配新任务到该节点
- 触发离线通知

### TC-NODE-011 节点恢复上线

**Given** 节点 `node_id=1` 状态为 OFFLINE
**When** 节点重新发送心跳
**Then**
- 节点状态变为 `ONLINE`
- 可正常接收新任务

### TC-NODE-012 心跳 — 节点不存在

**Given** 不存在 `node_id=99999`
**When** 调用 `POST /api/v1/nodes/99999/heartbeat`
**Then**
- 返回 HTTP 404
- 错误码 `NODE_NOT_FOUND`

---

## 4. 节点分组（FR-NODE-004）

### TC-NODE-013 创建节点组

**Given** 管理员已登录
**When** 调用 `POST /api/v1/nodes/groups`，请求体：
```json
{
  "name": "UI测试组",
  "description": "专门用于UI自动化测试的节点"
}
```
**Then**
- 返回 HTTP 201
- 节点组创建成功

### TC-NODE-014 将节点加入分组

**Given** 节点组 `group_id=1` 已创建，节点 `node_id=1` 未分组
**When** 调用 `PUT /api/v1/nodes/1`，请求体 `{"group_id": 1}`
**Then**
- 返回 HTTP 200
- 节点 `group_id` 更新为 1

### TC-NODE-015 查看节点组列表

**Given** 平台中存在 3 个节点组
**When** 调用 `GET /api/v1/nodes/groups`
**Then**
- 返回 HTTP 200
- 列表包含 3 个节点组
- 每个组包含 `name`、`description`、`node_count`

### TC-NODE-016 删除节点组

**Given** 节点组 `group_id=1` 下有 2 个节点
**When** 调用 `DELETE /api/v1/nodes/groups/1`
**Then**
- 返回 HTTP 200
- 节点组被删除
- 组内节点的 `group_id` 置为 NULL

---

## 5. 节点禁用/启用（FR-NODE-005）

### TC-NODE-017 禁用节点

**Given** 节点 `node_id=1` 状态为 ONLINE，当前有 0 个任务
**When** 调用 `PUT /api/v1/nodes/1`，请求体 `{"status": "DISABLED"}`
**Then**
- 返回 HTTP 200
- 节点状态变为 `DISABLED`
- 调度器不再分配新任务到该节点

### TC-NODE-018 禁用有任务执行中的节点

**Given** 节点 `node_id=1` 当前正在执行 2 个任务
**When** 调用 `PUT /api/v1/nodes/1`，请求体 `{"status": "DISABLED"}`
**Then**
- 返回 HTTP 200
- 节点状态变为 `DISABLED`
- 正在执行的 2 个任务继续完成
- 不再分配新任务

### TC-NODE-019 启用节点

**Given** 节点 `node_id=1` 状态为 DISABLED
**When** 调用 `PUT /api/v1/nodes/1`，请求体 `{"status": "ONLINE"}`
**Then**
- 返回 HTTP 200
- 节点状态变为 `ONLINE`
- 可正常接收新任务

### TC-NODE-020 操作不存在的节点

**Given** 不存在 `node_id=99999`
**When** 调用 `PUT /api/v1/nodes/99999`
**Then**
- 返回 HTTP 404
- 错误码 `NODE_NOT_FOUND`
