# E2E 验收测试用例 — 总索引

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md v1.0 + user-story.md v1.0

---

## 用例统计

| 模块 | 文件 | 用例数 | 覆盖需求 |
|------|------|--------|---------|
| AUTH 身份认证 | [E2E-AUTH.md](E2E-AUTH.md) | 25 | FR-AUTH-001 ~ FR-AUTH-006 |
| CASE 用例管理 | [E2E-CASE.md](E2E-CASE.md) | 25 | FR-CASE-001 ~ FR-CASE-006 |
| TASK 任务管理 | [E2E-TASK.md](E2E-TASK.md) | 25 | FR-TASK-001 ~ FR-TASK-004 |
| RESULT 结果展示 | [E2E-RESULT.md](E2E-RESULT.md) | 22 | FR-RESULT-001 ~ FR-RESULT-005 |
| NODE 节点管理 | [E2E-NODE.md](E2E-NODE.md) | 20 | FR-NODE-001 ~ FR-NODE-005 |
| SYS 系统管理 | [E2E-SYS.md](E2E-SYS.md) | 22 | FR-SYS-001 ~ FR-SYS-004 |
| EXEC 执行引擎 | [E2E-EXEC.md](E2E-EXEC.md) | 26 | FR-EXEC-001 ~ FR-EXEC-004 |
| **合计** | | **165** | **34 个功能需求** |

---

## 需求覆盖矩阵

| 需求编号 | 需求名称 | 测试用例 |
|---------|---------|---------|
| FR-AUTH-001 | 账号密码登录 | TC-AUTH-001 ~ 007 |
| FR-AUTH-002 | 退出登录 | TC-AUTH-008 ~ 009 |
| FR-AUTH-003 | Token 刷新 | TC-AUTH-010 ~ 011 |
| FR-AUTH-004 | 获取当前用户信息 | TC-AUTH-012 ~ 013 |
| FR-AUTH-005 | 密码找回 | TC-AUTH-014 ~ 018 |
| FR-AUTH-006 | 权限控制 | TC-AUTH-019 ~ 025 |
| FR-CASE-001 | 用例列表查询 | TC-CASE-001 ~ 006 |
| FR-CASE-002 | 创建用例 | TC-CASE-007 ~ 012 |
| FR-CASE-003 | 更新用例 | TC-CASE-013 ~ 015 |
| FR-CASE-004 | 删除用例 | TC-CASE-016 ~ 018 |
| FR-CASE-005 | 用例导入导出 | TC-CASE-019 ~ 022 |
| FR-CASE-006 | 用例版本管理 | TC-CASE-023 ~ 025 |
| FR-TASK-001 | 创建任务 | TC-TASK-001 ~ 007 |
| FR-TASK-002 | 任务调度 | TC-TASK-008 ~ 011 |
| FR-TASK-003 | 任务状态管理 | TC-TASK-012 ~ 019 |
| FR-TASK-004 | 任务日志 | TC-TASK-020 ~ 025 |
| FR-RESULT-001 | 结果概览 | TC-RESULT-001 ~ 004 |
| FR-RESULT-002 | 结果列表 | TC-RESULT-005 ~ 007 |
| FR-RESULT-003 | 结果详情 | TC-RESULT-008 ~ 011 |
| FR-RESULT-004 | 结果导出 | TC-RESULT-012 ~ 015 |
| FR-RESULT-005 | 结果分享 | TC-RESULT-016 ~ 022 |
| FR-NODE-001 | 节点注册 | TC-NODE-001 ~ 004 |
| FR-NODE-002 | 节点列表 | TC-NODE-005 ~ 008 |
| FR-NODE-003 | 节点心跳 | TC-NODE-009 ~ 012 |
| FR-NODE-004 | 节点分组 | TC-NODE-013 ~ 016 |
| FR-NODE-005 | 节点禁用/启用 | TC-NODE-017 ~ 020 |
| FR-SYS-001 | 操作日志 | TC-SYS-001 ~ 008 |
| FR-SYS-002 | 消息通知 | TC-SYS-009 ~ 013 |
| FR-SYS-003 | 系统配置 | TC-SYS-014 ~ 017 |
| FR-SYS-004 | 健康检查 | TC-SYS-018 ~ 021 |
| FR-EXEC-001 | Playwright UI 测试执行 | TC-EXEC-001 ~ 006 |
| FR-EXEC-002 | 接口测试执行 | TC-EXEC-007 ~ 015 |
| FR-EXEC-003 | Locust 性能压测执行 | TC-EXEC-016 ~ 021 |
| FR-EXEC-004 | UI 用例录制 | TC-EXEC-022 ~ 026 |

---

## 用例格式说明

每条用例采用 **Given / When / Then** 格式：
- **Given**：前置条件（数据准备、系统状态）
- **When**：触发动作（API 调用、用户操作）
- **Then**：预期结果（HTTP 状态码、响应体、数据库变更、UI 变化）
