# E2E 验收测试用例 — AUTH 身份认证模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-AUTH-001 ~ FR-AUTH-006

---

## 1. 账号密码登录（FR-AUTH-001）

### TC-AUTH-001 正常登录

**Given** 用户 `tester01` 已在平台注册，角色为 TESTER，账号状态为启用
**When** 用户输入用户名 `tester01` 和正确密码，点击登录按钮
**Then**
- 返回 HTTP 200
- 响应体 `code=0`
- 响应体包含 `token`（JWT 格式，三段式）
- 响应体 `data.user.username = "tester01"`
- 响应体 `data.user.role` 包含 `TESTER`
- 页面跳转到仪表盘

### TC-AUTH-002 密码错误

**Given** 用户 `tester01` 已注册
**When** 用户输入用户名 `tester01` 和错误密码 `wrong_pass`，点击登录
**Then**
- 返回 HTTP 401
- 错误码 `INVALID_CREDENTIALS`
- 提示信息为"用户名或密码错误"（不泄露具体哪个字段错误）
- 不返回 token

### TC-AUTH-003 用户不存在

**Given** 系统中不存在用户 `nonexistent_user`
**When** 用户输入用户名 `nonexistent_user` 和任意密码，点击登录
**Then**
- 返回 HTTP 401
- 错误码 `INVALID_CREDENTIALS`
- 提示信息为"用户名或密码错误"（与密码错误提示一致，防止用户名枚举）

### TC-AUTH-004 账号禁用

**Given** 用户 `disabled_user` 已注册但 `is_active=false`
**When** 用户输入正确的用户名和密码，点击登录
**Then**
- 返回 HTTP 403
- 错误码 `ACCOUNT_DISABLED`
- 提示信息为"账号已禁用，请联系管理员"
- 不返回 token

### TC-AUTH-005 账号锁定（连续失败5次）

**Given** 用户 `tester01` 已注册，当前未锁定
**When** 用户连续输入错误密码 5 次，第 6 次尝试登录
**Then**
- 前 5 次均返回 HTTP 401，错误码 `INVALID_CREDENTIALS`
- 第 6 次返回 HTTP 423
- 错误码 `ACCOUNT_LOCKED`
- 提示信息包含"账号已锁定"和剩余锁定时间
- 即使输入正确密码也无法登录
- 数据库中 `users.locked_until` 被设置为 1 小时后

### TC-AUTH-006 登录参数校验 — 用户名为空

**Given** 用户在登录页面
**When** 不输入用户名，输入密码，点击登录
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"用户名不能为空"

### TC-AUTH-007 登录参数校验 — 密码为空

**Given** 用户在登录页面
**When** 输入用户名，不输入密码，点击登录
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示"密码不能为空"

---

## 2. 退出登录（FR-AUTH-002）

### TC-AUTH-008 正常退出

**Given** 用户 `tester01` 已登录，持有有效 Token
**When** 用户点击退出登录
**Then**
- 返回 HTTP 200
- Token 加入 Redis 黑名单
- 本地 Token 被清除
- 页面跳转到登录页

### TC-AUTH-009 退出后 Token 失效

**Given** 用户 `tester01` 已退出登录（Token 已加入黑名单）
**When** 使用旧 Token 访问受保护的 API（如 `GET /api/v1/auth/me`）
**Then**
- 返回 HTTP 401
- 错误码 `TOKEN_REVOKED`

---

## 3. Token 刷新（FR-AUTH-003）

### TC-AUTH-010 正常刷新 Token

**Given** 用户 `tester01` 已登录，持有有效 Token
**When** 调用 `POST /api/v1/auth/refresh-token`，携带当前 Token
**Then**
- 返回 HTTP 200
- 返回新的 Token
- 旧 Token 立即失效（加入黑名单）
- 新 Token 可正常用于 API 访问

### TC-AUTH-011 使用过期 Token 刷新

**Given** 用户的 Token 已过期
**When** 调用 `POST /api/v1/auth/refresh-token`
**Then**
- 返回 HTTP 401
- 错误码 `TOKEN_INVALID`
- 不返回新 Token

---

## 4. 获取当前用户信息（FR-AUTH-004）

### TC-AUTH-012 获取当前用户信息

**Given** 用户 `tester01` 已登录，角色为 TESTER
**When** 调用 `GET /api/v1/auth/me`
**Then**
- 返回 HTTP 200
- 响应体包含 `id`、`username="tester01"`、`role`、`permissions` 列表
- permissions 包含 TESTER 角色对应的权限

### TC-AUTH-013 未登录访问

**Given** 用户未登录（无 Token）
**When** 调用 `GET /api/v1/auth/me`
**Then**
- 返回 HTTP 401
- 错误码 `TOKEN_INVALID`

---

## 5. 密码找回（FR-AUTH-005）

### TC-AUTH-014 发送验证码

**Given** 用户 `tester01` 已绑定邮箱 `test@example.com`
**When** 调用 `POST /api/v1/auth/forgot-password`，传入用户名 `tester01`
**Then**
- 返回 HTTP 200
- 验证码发送到绑定邮箱
- 验证码存储在 Redis，有效期 5 分钟

### TC-AUTH-015 验证码正确 — 重置密码

**Given** 用户已收到验证码 `123456`
**When** 先调用 `POST /api/v1/auth/verify-code` 验证验证码，再调用 `POST /api/v1/auth/reset-password` 设置新密码 `NewPass@123`
**Then**
- 验证码校验返回 HTTP 200
- 密码重置返回 HTTP 200
- 旧密码失效
- 新密码可正常登录

### TC-AUTH-016 验证码错误

**Given** 用户已请求验证码
**When** 调用 `POST /api/v1/auth/verify-code`，传入错误验证码 `000000`
**Then**
- 返回 HTTP 400
- 提示"验证码错误"

### TC-AUTH-017 验证码过期

**Given** 用户已请求验证码，等待超过 5 分钟
**When** 调用 `POST /api/v1/auth/verify-code`，传入正确验证码
**Then**
- 返回 HTTP 400
- 提示"验证码已过期，请重新获取"

### TC-AUTH-018 新密码不符合复杂度

**Given** 用户已通过验证码校验
**When** 调用 `POST /api/v1/auth/reset-password`，设置新密码为 `123`（不足 8 位）
**Then**
- 返回 HTTP 422
- 错误码 `VALIDATION_ERROR`
- 提示密码需包含字母+数字+特殊符号，长度≥8 位

---

## 6. 权限控制（FR-AUTH-006）

### TC-AUTH-019 ADMIN 角色全功能访问

**Given** 用户 `admin01` 角色为 ADMIN，已登录
**When** 依次访问以下 API：
- `GET /api/v1/cases`（用例管理）
- `POST /api/v1/tasks`（任务管理）
- `GET /api/v1/nodes`（节点管理）
- `GET /api/v1/system/config`（系统配置）
**Then**
- 所有请求均返回 HTTP 200/201
- 可执行 CRUD 操作

### TC-AUTH-020 TESTER 角色权限验证

**Given** 用户 `tester01` 角色为 TESTER，已登录
**When** 访问用例管理 API（`GET/POST/PUT /api/v1/cases`）
**Then**
- 返回 HTTP 200/201，操作成功

**When** 访问用户管理 API（`POST /api/v1/users`）
**Then**
- 返回 HTTP 403
- 错误码 `FORBIDDEN`
- 提示"权限不足"

### TC-AUTH-021 OPS 角色权限验证

**Given** 用户 `ops01` 角色为 OPS，已登录
**When** 访问节点管理 API（`GET/POST/PUT /api/v1/nodes`）
**Then**
- 返回 HTTP 200/201，操作成功

**When** 访问用例创建 API（`POST /api/v1/cases`）
**Then**
- 返回 HTTP 403
- 错误码 `FORBIDDEN`

### TC-AUTH-022 OPS 只读用例

**Given** 用户 `ops01` 角色为 OPS，已登录
**When** 调用 `GET /api/v1/cases` 查看用例列表
**Then**
- 返回 HTTP 200，可查看

**When** 调用 `POST /api/v1/cases` 创建用例
**Then**
- 返回 HTTP 403，错误码 `FORBIDDEN`

---

## 7. 安全防护

### TC-AUTH-023 登录日志记录

**Given** 用户 `tester01` 尝试登录
**When** 登录成功或失败
**Then**
- 系统日志表 `system_logs` 新增一条记录
- 包含：操作人 ID、操作类型 LOGIN、资源类型 USER、登录 IP、登录状态

### TC-AUTH-024 密码加密存储

**Given** 用户 `tester01` 已注册
**When** 查看数据库 `users` 表
**Then**
- `password_hash` 字段为 bcrypt 格式（`$2b$` 开头）
- 明文密码不存储在任何地方

### TC-AUTH-025 JWT Token 有效期

**Given** 用户 `tester01` 已登录获得 Token
**When** Token 超过配置的有效期后使用
**Then**
- 返回 HTTP 401
- 错误码 `TOKEN_INVALID`
