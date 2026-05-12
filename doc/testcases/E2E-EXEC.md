# E2E 验收测试用例 — EXEC 执行引擎模块

> 版本：1.0 | 日期：2026-05-12 | 需求基线：requirement.md FR-EXEC-001 ~ FR-EXEC-004

---

## 1. Playwright UI 测试执行（FR-EXEC-001）

### TC-EXEC-001 UI 用例正常执行

**Given** 一个 UI 测试用例，脚本内容为登录页面验证，目标节点在线
**When** 任务调度到节点执行该用例
**Then**
- 引擎创建浏览器上下文（Chromium）
- 脚本执行成功
- 每个断言步骤自动截图
- 结果写入 `test_results` 表，`status=SUCCESS`
- `duration_ms` > 0

### TC-EXEC-002 UI 用例执行失败 — 断言失败

**Given** 一个 UI 测试用例，脚本中断言期望页面标题为"首页"，实际为"登录"
**When** 执行该用例
**Then**
- 脚本执行到断言步骤时捕获 AssertionError
- 自动截图保存失败现场
- 结果 `status=FAILED`
- `detail` 中包含：失败步骤、预期值、实际值、截图路径
- 失败用例自动录制执行过程视频

### TC-EXEC-003 UI 用例执行超时

**Given** 一个 UI 测试用例，脚本等待一个不存在的元素，默认超时 60s
**When** 执行该用例
**Then**
- 60 秒后触发超时异常
- 结果 `status=FAILED`
- 错误信息包含"执行超时"
- 截图保存超时前的页面状态

### TC-EXEC-004 UI 用例 — 跨浏览器执行

**Given** 一个 UI 测试用例配置了多浏览器执行
**When** 任务执行
**Then**
- 分别在 Chromium、Firefox、WebKit 下执行
- 生成 3 条结果记录
- 每条记录的 `detail.browser` 标识浏览器类型

### TC-EXEC-005 UI 用例 — 脚本语法错误

**Given** 一个 UI 测试用例，脚本包含语法错误
**When** 引擎尝试执行
**Then**
- 执行前校验脚本有效性
- 结果 `status=FAILED`
- 错误信息包含具体的语法错误位置

### TC-EXEC-006 UI 用例 — 截图与录像采集

**Given** 一个 UI 测试用例执行完成（包含成功和失败步骤）
**When** 查看执行结果
**Then**
- 成功步骤：每个断言点有一张截图
- 失败步骤：有额外的失败现场截图
- 失败用例：有完整的执行录像文件
- 截图路径和录像路径记录在结果 `detail` 中

---

## 2. 接口测试执行（FR-EXEC-002）

### TC-EXEC-007 接口用例正常执行

**Given** 一个接口测试用例：`POST /api/v1/auth/login`，断言状态码=200
**When** 引擎执行该用例
**Then**
- 发送 HTTP 请求到目标接口
- 收到响应
- 断言通过：`status_code == 200`
- 结果 `status=SUCCESS`
- `detail` 包含完整的请求/响应信息

### TC-EXEC-008 接口用例 — 断言失败

**Given** 一个接口用例，断言状态码=200，实际接口返回 500
**When** 执行该用例
**Then**
- 结果 `status=FAILED`
- `detail.assertions` 中该断言 `pass=false`
- 记录 `expected=200`、`actual=500`

### TC-EXEC-009 接口用例 — JSONPath 断言

**Given** 一个接口用例，断言 `$.code == 0`
**When** 执行该用例，响应体为 `{"code": 0, "data": {...}}`
**Then**
- JSONPath 断言通过
- 结果 `status=SUCCESS`

### TC-EXEC-010 接口用例 — 响应时间断言

**Given** 一个接口用例，断言响应时间 ≤ 1000ms
**When** 执行该用例，实际响应时间为 500ms
**Then**
- 响应时间断言通过
- `detail.duration_ms=500`

### TC-EXEC-011 接口用例 — 响应时间超限

**Given** 一个接口用例，断言响应时间 ≤ 500ms
**When** 执行该用例，实际响应时间为 1500ms
**Then**
- 结果 `status=FAILED`
- 响应时间断言 `pass=false`
- 记录 `expected=500`、`actual=1500`

### TC-EXEC-012 接口依赖 — 参数传递

**Given** 两个接口用例有依赖关系：
- 用例 A：`POST /login`，提取响应中 `$.data.token`
- 用例 B：`GET /user/me`，请求头 Authorization 依赖用例 A 的 token
**When** 按顺序执行
**Then**
- 用例 A 执行成功，提取到 token
- 用例 B 的请求头自动注入 `Authorization: Bearer {token}`
- 两个用例均执行成功

### TC-EXEC-013 接口依赖 — 前置接口失败

**Given** 两个接口用例有依赖关系
**When** 用例 A 执行失败
**Then**
- 用例 B 标记为 `SKIPPED`
- 用例 B 的结果 `detail` 记录跳过原因："前置接口执行失败"

### TC-EXEC-014 接口用例 — 请求超时

**Given** 一个接口用例，`api_timeout=5000`（5 秒）
**When** 目标接口响应时间超过 5 秒
**Then**
- 结果 `status=FAILED`
- 错误信息包含"请求超时"

### TC-EXEC-015 接口用例 — 多种请求方法

**Given** 4 个接口用例，分别使用 GET、POST、PUT、DELETE 方法
**When** 分别执行
**Then**
- 每个用例使用对应的 HTTP 方法发送请求
- 方法正确记录在结果 `detail.method` 中

---

## 3. Locust 性能压测执行（FR-EXEC-003）

### TC-EXEC-016 性能用例正常执行

**Given** 一个性能用例：100 并发用户，增长率 10/s，持续 60 秒
**When** 引擎执行该用例
**Then**
- 生成 locustfile
- 启动 Locust 压测
- 按配置逐步增加用户到 100
- 持续 60 秒后停止
- 采集指标：RPS、P50/P95/P99 响应时间、错误率
- 结果 `status=SUCCESS`

### TC-EXEC-017 性能用例 — 分布式执行

**Given** 一个性能用例需要 500 并发用户，配置 master + 2 worker 模式
**When** 引擎执行该用例
**Then**
- master 节点启动协调
- 2 个 worker 节点分担负载
- 总并发用户数 = 500
- 各 worker 的负载分配均匀

### TC-EXEC-018 性能用例 — P95 断言失败

**Given** 一个性能用例，断言 P95 响应时间 ≤ 500ms
**When** 执行完成，实际 P95 = 800ms
**Then**
- 结果 `status=FAILED`
- 性能断言 `pass=false`
- 记录 `expected=500`、`actual=800`

### TC-EXEC-019 性能用例 — 错误率断言

**Given** 一个性能用例，断言错误率 ≤ 1%
**When** 执行完成，实际错误率 = 5%
**Then**
- 结果 `status=FAILED`
- 错误率断言 `pass=false`

### TC-EXEC-020 性能用例 — Locust 脚本自定义

**Given** 一个性能用例，用户编写了自定义 Locust 脚本（包含复杂的用户行为模拟）
**When** 引擎执行该用例
**Then**
- 使用用户自定义的 locustfile
- 脚本语法校验通过后执行
- 执行结果包含自定义指标

### TC-EXEC-021 性能用例 — HTML 报告生成

**Given** 性能压测执行完成
**When** 查看结果详情
**Then**
- 包含 Locust 原生 HTML 报告的访问路径
- 包含结构化数据：RPS 时间序列、响应时间分布、用户数变化曲线

---

## 4. UI 用例录制（FR-EXEC-004）

### TC-EXEC-022 启动录制器

**Given** 用户已登录，选择"录制模式"创建 UI 用例
**When** 点击"开始录制"
**Then**
- 启动 Playwright Codegen 录制浏览器
- 浏览器打开指定的目标 URL
- 录制状态指示器显示"录制中"

### TC-EXEC-023 录制操作生成脚本

**Given** 录制器已启动
**When** 用户在浏览器中执行操作：点击登录按钮、输入用户名、输入密码、点击提交
**Then**
- 实时生成 Playwright Python 脚本
- 脚本包含对应的操作代码
- 代码编辑器中同步显示生成的脚本

### TC-EXEC-024 保存录制用例

**Given** 录制完成，脚本已生成
**When** 用户点击"保存"
**Then**
- 用例保存成功
- `ui_script_type=RECORDED`
- `ui_script` 包含完整的 Playwright 脚本
- 可在用例列表中查看和编辑

### TC-EXEC-025 录制脚本回放验证

**Given** 一个录制模式创建的 UI 用例
**When** 用户点击"回放验证"
**Then**
- 使用录制的脚本重新执行
- 执行过程在浏览器中可视化展示
- 执行结果与录制时一致

### TC-EXEC-026 录制脚本编辑

**Given** 一个录制模式创建的 UI 用例
**When** 用户在 Monaco Editor 中编辑脚本
**Then**
- 编辑器支持 Python 语法高亮
- 支持自动补全（Playwright API）
- 保存时检查脚本语法有效性
- `ui_script_type` 变为 `MANUAL`
