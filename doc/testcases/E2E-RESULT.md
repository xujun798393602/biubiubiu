# E2E 验收测试用例 — RESULT 结果展示模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-RESULT-001 ~ FR-RESULT-005

---

## 1. 结果概览（FR-RESULT-001）

### TC-RESULT-001 任务结果统计

**Given** 任务 `task_id=100` 已执行完成，包含 10 个用例：7 成功、2 失败、1 跳过
**When** 调用 `GET /api/v1/results/overview?taskId=100`
**Then**
- 返回 HTTP 200
- `totalCases=10`
- `successCount=7`
- `failedCount=2`
- `skippedCount=1`
- `successRate=0.7`（70%）
- `duration` > 0（执行时长，单位毫秒）

### TC-RESULT-002 结果概览 — 全部成功

**Given** 任务执行完成，5 个用例全部成功
**When** 调用 `GET /api/v1/results/overview?taskId={id}`
**Then**
- `totalCases=5`
- `successCount=5`
- `failedCount=0`
- `successRate=1.0`（100%）

### TC-RESULT-003 结果概览 — 任务不存在

**Given** 不存在 `task_id=99999`
**When** 调用 `GET /api/v1/results/overview?taskId=99999`
**Then**
- 返回 HTTP 404
- 错误码 `TASK_NOT_FOUND`

### TC-RESULT-004 结果概览 — 任务未完成

**Given** 任务 `task_id=100` 状态为 RUNNING
**When** 调用 `GET /api/v1/results/overview?taskId=100`
**Then**
- 返回 HTTP 200
- 统计数据反映当前已执行的部分结果
- 可能包含 `status=RUNNING` 标识

---

## 2. 结果列表（FR-RESULT-002）

### TC-RESULT-005 查看结果列表

**Given** 任务 `task_id=100` 已执行完成，有 10 条结果记录
**When** 调用 `GET /api/v1/results?taskId=100`
**Then**
- 返回 HTTP 200
- 分页列表，每条记录包含：`case_name`、`case_type`、`status`（SUCCESS/FAILED/SKIPPED）、`duration_ms`、`executed_at`
- 按执行时间正序排列

### TC-RESULT-006 按状态筛选结果

**Given** 任务有 7 条成功、2 条失败、1 条跳过的结果
**When** 调用 `GET /api/v1/results?taskId=100&status=FAILED`
**Then**
- 仅返回 status=FAILED 的结果
- 共 2 条

### TC-RESULT-007 结果列表分页

**Given** 任务有 25 条结果
**When** 调用 `GET /api/v1/results?taskId=100&page=2&pageSize=10`
**Then**
- 返回第 11~20 条结果
- `total=25`

---

## 3. 结果详情（FR-RESULT-003）

### TC-RESULT-008 接口测试结果详情

**Given** 一条接口测试结果 `result_id=200`
**When** 调用 `GET /api/v1/results/api/200`
**Then**
- 返回 HTTP 200
- 包含完整信息：
  - 请求信息：URL、Method、Headers、Body
  - 响应信息：Status Code、Response Body、Response Headers
  - 断言结果：每条断言的 expected vs actual、pass/fail
  - 执行耗时（ms）

### TC-RESULT-009 UI 测试结果详情

**Given** 一条 UI 测试结果 `result_id=201`，执行失败
**When** 调用 `GET /api/v1/results/api/201`
**Then**
- 返回 HTTP 200
- 包含：
  - 执行步骤列表
  - 每步的实际结果和预期结果
  - 失败步骤的错误截图路径（`screenshots` 字段）
  - 执行录像路径（`video_path` 字段）
  - 错误日志

### TC-RESULT-010 性能测试结果详情

**Given** 一条性能测试结果 `result_id=202`
**When** 调用 `GET /api/v1/results/api/202`
**Then**
- 返回 HTTP 200
- 包含：
  - 并发用户数
  - 吞吐量（RPS）
  - 响应时间：P50、P95、P99
  - 错误率
  - Locust HTML 报告路径
  - 趋势图数据

### TC-RESULT-011 结果详情 — 不存在

**Given** 不存在 `result_id=99999`
**When** 调用 `GET /api/v1/results/api/99999`
**Then**
- 返回 HTTP 404
- 错误码 `RESULT_NOT_FOUND`

---

## 4. 结果导出（FR-RESULT-004）

### TC-RESULT-012 导出为 Excel

**Given** 任务 `task_id=100` 已执行完成
**When** 调用 `POST /api/v1/results/100/export`，请求体 `{"format": "xlsx"}`
**Then**
- 返回 HTTP 200
- Content-Type 为 Excel 格式
- 文件包含：结果概览统计、每条用例的详细结果
- 包含表头和数据行

### TC-RESULT-013 导出为 PDF

**Given** 任务 `task_id=100` 已执行完成
**When** 调用 `POST /api/v1/results/100/export`，请求体 `{"format": "pdf"}`
**Then**
- 返回 HTTP 200
- Content-Type 为 `application/pdf`
- PDF 包含测试报告：概览、结果列表、统计图表

### TC-RESULT-014 导出为 HTML

**Given** 任务 `task_id=100` 已执行完成
**When** 调用 `POST /api/v1/results/100/export`，请求体 `{"format": "html"}`
**Then**
- 返回 HTTP 200
- Content-Type 为 `text/html`
- HTML 包含完整的测试报告，可在浏览器中查看

### TC-RESULT-015 导出 — 任务不存在

**Given** 不存在 `task_id=99999`
**When** 调用 `POST /api/v1/results/99999/export`
**Then**
- 返回 HTTP 404
- 错误码 `TASK_NOT_FOUND`

---

## 5. 结果分享（FR-RESULT-005）

### TC-RESULT-016 生成分享链接

**Given** 任务 `task_id=100` 已执行完成，当前用户已登录
**When** 调用 `POST /api/v1/results/100/share`，请求体：
```json
{
  "expires_in_hours": 24,
  "password": "share123"
}
```
**Then**
- 返回 HTTP 200
- 响应体包含 `share_url`（含 token）
- 数据库 `result_shares` 表新增一条记录
- `expires_at` 为 24 小时后

### TC-RESULT-017 无密码分享

**Given** 任务执行完成
**When** 调用 `POST /api/v1/results/100/share`，不传 `password`
**Then**
- 返回 HTTP 200
- 生成的分享链接无需密码即可访问

### TC-RESULT-018 访问分享链接 — 有效

**Given** 已生成分享链接，token=`abc123`，未过期，无密码
**When** 调用 `GET /api/v1/results/share/abc123`（无需认证）
**Then**
- 返回 HTTP 200
- 返回测试结果数据（概览+列表）

### TC-RESULT-019 访问分享链接 — 需要密码

**Given** 分享链接设置了密码
**When** 调用 `GET /api/v1/results/share/{token}`，不提供密码
**Then**
- 返回 HTTP 401
- 错误码 `SHARE_PASSWORD_REQUIRED`

### TC-RESULT-020 访问分享链接 — 密码错误

**Given** 分享链接密码为 `share123`
**When** 调用 `GET /api/v1/results/share/{token}?password=wrong`
**Then**
- 返回 HTTP 401
- 错误码 `SHARE_PASSWORD_INVALID`

### TC-RESULT-021 访问分享链接 — 已过期

**Given** 分享链接已超过有效期
**When** 调用 `GET /api/v1/results/share/{token}`
**Then**
- 返回 HTTP 410
- 错误码 `SHARE_EXPIRED`

### TC-RESULT-022 访问分享链接 — 不存在

**Given** token 不存在
**When** 调用 `GET /api/v1/results/share/nonexistent`
**Then**
- 返回 HTTP 404
- 错误码 `SHARE_NOT_FOUND`
