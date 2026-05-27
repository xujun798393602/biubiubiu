<template>
  <div class="task-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>任务管理</span>
          <div class="header-actions">
            <el-input v-model="filters.keyword" placeholder="搜索任务名称" clearable style="width:180px" @clear="fetchData" @keyup.enter="fetchData">
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
            <el-select v-model="filters.creator_id" placeholder="筛选创建人" clearable style="width:150px" @change="fetchData">
              <el-option v-for="c in creators" :key="c.id" :label="c.username" :value="c.id" />
            </el-select>
            <el-button type="primary" icon="Plus" @click="handleCreate">新建任务</el-button>
          </div>
        </div>
      </template>
      <el-table :data="taskList" v-loading="loading" stripe border>
        <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='SUCCESS'?'success':row.status==='FAILED'?'danger':row.status==='RUNNING'?'warning':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="creator_name" label="创建人" width="110" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80"><template #default="{row}"><el-tag :type="row.priority==='HIGH'?'danger':'warning'" size="small">{{ row.priority }}</el-tag></template></el-table-column>
        <el-table-column prop="total_cases" label="用例数" width="80" />
        <el-table-column prop="success_count" label="通过" width="80" />
        <el-table-column prop="failed_count" label="失败" width="80" />
        <el-table-column prop="skipped_count" label="跳过" width="80" />
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{row}">
            <el-button text type="primary" size="small" @click="handleStart(row)" :disabled="row.status==='RUNNING'">启动</el-button>
            <el-button text type="warning" size="small" @click="handleCancel(row)" :disabled="row.status!=='RUNNING'">取消</el-button>
            <el-button text type="primary" size="small" @click="handleShowResult(row)">结果</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10,20,50]" layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
    </el-card>

    <!-- 结果展示弹窗 -->
    <el-dialog v-model="resultDialogVisible" :title="`结果展示 - ${currentTaskName}`" width="85%" top="3vh" destroy-on-close class="result-dialog">
      <div class="result-dialog-content">
        <el-row v-if="resultOverview" :gutter="16" class="overview-row">
          <el-col :span="5"><div class="overview-item"><div class="overview-label">总用例数</div><div class="overview-value">{{ resultOverview.totalCases }}</div></div></el-col>
          <el-col :span="5"><div class="overview-item success"><div class="overview-label">通过</div><div class="overview-value">{{ resultOverview.successCount }}</div></div></el-col>
          <el-col :span="5"><div class="overview-item danger"><div class="overview-label">失败</div><div class="overview-value">{{ resultOverview.failedCount }}</div></div></el-col>
          <el-col :span="5"><div class="overview-item"><div class="overview-label">跳过</div><div class="overview-value">{{ resultOverview.skippedCount }}</div></div></el-col>
          <el-col :span="4"><div class="overview-item"><div class="overview-label">通过率</div><div class="overview-value">{{ resultOverview.successRate }}%</div></div></el-col>
        </el-row>

        <el-table :data="resultList" v-loading="resultLoading" stripe border>
          <el-table-column prop="caseName" label="用例名称" min-width="200" show-overflow-tooltip />
          <el-table-column prop="caseType" label="类型" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.caseType === 'UI' ? 'warning' : row.caseType === 'API' ? '' : 'danger'">
                {{ ({ UI: 'UI 测试', API: '接口测试', PERFORMANCE: '性能压测' } as Record<string, string>)[row.caseType] || row.caseType }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="结果" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'SUCCESS' ? 'success' : row.status === 'FAILED' ? 'danger' : 'info'" size="small">
                {{ ({ SUCCESS: '通过', FAILED: '失败', SKIPPED: '跳过' } as Record<string, string>)[row.status] || row.status }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="duration" label="耗时(秒)" width="100" />
          <el-table-column prop="startedAt" label="开始时间" width="170"><template #default="{ row }">{{ formatDate(row.startedAt) }}</template></el-table-column>
          <el-table-column prop="finishedAt" label="结束时间" width="170"><template #default="{ row }">{{ formatDate(row.finishedAt) }}</template></el-table-column>
          <el-table-column label="操作" width="100" fixed="right"><template #default="{ row }"><el-button text type="primary" size="small" @click="handleDetail(row)">详情</el-button></template></el-table-column>
        </el-table>

        <el-pagination class="pagination" v-model:current-page="resultPagination.page" v-model:page-size="resultPagination.pageSize" :total="resultPagination.total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @size-change="fetchResults" @current-change="fetchResults" />
      </div>
    </el-dialog>

    <!-- 用例详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="用例详情" width="60%" top="5vh" destroy-on-close class="detail-dialog">
      <div v-if="currentDetail" class="detail-content">
        <el-descriptions :column="2" border class="detail-info">
          <el-descriptions-item label="用例名称">{{ currentDetail.case_name }}</el-descriptions-item>
          <el-descriptions-item label="用例类型">
            <el-tag size="small" :type="currentDetail.case_type === 'UI' ? 'warning' : currentDetail.case_type === 'API' ? '' : 'danger'">
              {{ ({ UI: 'UI 测试', API: '接口测试', PERFORMANCE: '性能压测' } as Record<string, string>)[currentDetail.case_type] || currentDetail.case_type }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行状态">
            <el-tag :type="currentDetail.status === 'SUCCESS' ? 'success' : currentDetail.status === 'FAILED' ? 'danger' : 'info'" size="small">
              {{ ({ SUCCESS: '通过', FAILED: '失败', SKIPPED: '跳过' } as Record<string, string>)[currentDetail.status] || currentDetail.status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行耗时">{{ (currentDetail.duration_ms / 1000).toFixed(2) }} 秒</el-descriptions-item>
        </el-descriptions>

        <div class="detail-section">
          <h4>执行详情</h4>
          <div v-if="currentDetail.detail" class="detail-json">
            <template v-if="currentDetail.case_type === 'API'">
              <div v-if="currentDetail.detail.url" class="detail-item">
                <span class="detail-label">请求地址:</span>
                <span>{{ currentDetail.detail.method }} {{ currentDetail.detail.url }}</span>
              </div>
              <div v-if="currentDetail.detail.status_code" class="detail-item">
                <span class="detail-label">状态码:</span>
                <el-tag :type="currentDetail.detail.status_code >= 200 && currentDetail.detail.status_code < 300 ? 'success' : 'danger'" size="small">
                  {{ currentDetail.detail.status_code }}
                </el-tag>
              </div>
              <div v-if="currentDetail.detail.response_time_ms" class="detail-item">
                <span class="detail-label">响应时间:</span>
                <span>{{ currentDetail.detail.response_time_ms }} ms</span>
              </div>
              <div v-if="currentDetail.detail.response_body" class="detail-item">
                <span class="detail-label">响应内容:</span>
                <el-input type="textarea" :model-value="currentDetail.detail.response_body" :rows="4" readonly />
              </div>
              <div v-if="currentDetail.detail.assertions" class="detail-item">
                <span class="detail-label">断言结果:</span>
                <el-table :data="currentDetail.detail.assertions" size="small" border>
                  <el-table-column prop="type" label="类型" width="120" />
                  <el-table-column prop="expected" label="期望值" />
                  <el-table-column prop="actual" label="实际值" />
                  <el-table-column label="结果" width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.passed ? 'success' : 'danger'" size="small">{{ row.passed ? '通过' : '失败' }}</el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </template>
            <template v-else-if="currentDetail.case_type === 'UI'">
              <div v-if="currentDetail.detail.exit_code !== undefined" class="detail-item">
                <span class="detail-label">退出码:</span>
                <el-tag :type="currentDetail.detail.exit_code === 0 ? 'success' : 'danger'" size="small">{{ currentDetail.detail.exit_code }}</el-tag>
                <span v-if="currentDetail.detail.total_steps" class="step-count">共 {{ currentDetail.detail.total_steps }} 个步骤</span>
              </div>

              <!-- 执行步骤时间轴 -->
              <div v-if="currentDetail.detail.steps && currentDetail.detail.steps.length > 0" class="detail-item">
                <span class="detail-label">执行步骤:</span>
                <div class="steps-timeline">
                  <el-timeline>
                    <el-timeline-item
                      v-for="step in currentDetail.detail.steps"
                      :key="step.step_index"
                      :type="step.status === 'success' ? 'success' : 'danger'"
                      :timestamp="step.timestamp ? new Date(step.timestamp).toLocaleTimeString('zh-CN') : ''"
                      placement="top"
                    >
                      <el-card class="step-card" shadow="hover">
                        <div class="step-header">
                          <span class="step-title">步骤 {{ step.step_index }}</span>
                          <el-tag :type="step.status === 'success' ? 'success' : 'danger'" size="small">
                            {{ step.status === 'success' ? '成功' : '失败' }}
                          </el-tag>
                          <span v-if="step.duration_ms" class="step-duration">{{ step.duration_ms }}ms</span>
                        </div>
                        <div class="step-code">
                          <code>{{ step.code }}</code>
                        </div>
                        <div v-if="step.log" class="step-log">
                          <el-icon><Document /></el-icon>
                          <span>{{ step.log }}</span>
                        </div>
                        <div v-if="step.screenshot" class="step-screenshot">
                          <el-image
                            :src="'data:image/jpeg;base64,' + step.screenshot"
                            :preview-src-list="['data:image/jpeg;base64,' + step.screenshot]"
                            fit="contain"
                            preview-teleported
                          >
                            <template #error>
                              <div class="image-error">截图加载失败</div>
                            </template>
                          </el-image>
                        </div>
                      </el-card>
                    </el-timeline-item>
                  </el-timeline>
                </div>
              </div>

              <!-- 完整日志 -->
              <div v-if="currentDetail.detail.stdout" class="detail-item">
                <span class="detail-label">执行日志:</span>
                <el-input type="textarea" :model-value="currentDetail.detail.stdout" :rows="6" readonly />
              </div>
              <div v-if="currentDetail.detail.stderr" class="detail-item">
                <span class="detail-label">错误输出:</span>
                <el-input type="textarea" :model-value="currentDetail.detail.stderr" :rows="3" readonly class="error-output" />
              </div>
            </template>
            <template v-else-if="currentDetail.case_type === 'PERFORMANCE'">
              <!-- 执行参数 -->
              <div class="detail-item">
                <span class="detail-label">执行参数:</span>
                <div class="perf-params">
                  <div class="perf-param-item">
                    <span class="perf-param-label">并发用户</span>
                    <span class="perf-param-value">{{ currentDetail.detail.vusers }}</span>
                  </div>
                  <div class="perf-param-item">
                    <span class="perf-param-label">启动速率</span>
                    <span class="perf-param-value">{{ currentDetail.detail.spawn_rate }}/s</span>
                  </div>
                  <div class="perf-param-item">
                    <span class="perf-param-label">持续时间</span>
                    <span class="perf-param-value">{{ currentDetail.detail.duration }}s</span>
                  </div>
                  <div class="perf-param-item">
                    <span class="perf-param-label">退出码</span>
                    <span class="perf-param-value"><el-tag :type="currentDetail.detail.exit_code === 0 ? 'success' : 'danger'" size="small">{{ currentDetail.detail.exit_code }}</el-tag></span>
                  </div>
                </div>
              </div>

              <!-- STATISTICS 统计表格 (仅已完成时展示) -->
              <div v-if="(currentDetail.status === 'SUCCESS' || currentDetail.status === 'FAILED') && currentDetail.detail.stats && currentDetail.detail.stats.endpoints && currentDetail.detail.stats.endpoints.length > 0" class="detail-item">
                <span class="detail-label">STATISTICS:</span>
                <el-table :data="perfTableData" size="small" border style="margin-top:8px" stripe :summary-method="getPerfSummary" show-summary>
                  <el-table-column prop="type" label="Type" width="80" align="center">
                    <template #default="{row}"><el-tag size="small" :type="row.type === 'GET' ? '' : row.type === 'POST' ? 'success' : 'warning'">{{ row.type }}</el-tag></template>
                  </el-table-column>
                  <el-table-column prop="name" label="Name" min-width="200" show-overflow-tooltip />
                  <el-table-column prop="requests" label="# requests" width="100" align="right" />
                  <el-table-column prop="failures" label="# failures" width="100" align="right">
                    <template #default="{row}"><span :class="row.failures > 0 ? 'text-danger' : ''">{{ row.failures }}</span></template>
                  </el-table-column>
                  <el-table-column prop="median_ms" label="Median (ms)" width="110" align="right" />
                  <el-table-column prop="avg_ms" label="Average (ms)" width="110" align="right" />
                  <el-table-column prop="min_ms" label="Min (ms)" width="90" align="right" />
                  <el-table-column prop="max_ms" label="Max (ms)" width="90" align="right" />
                  <el-table-column prop="avg_content_length" label="Avg Size" width="90" align="right" />
                  <el-table-column prop="rps" label="RPS" width="80" align="right" />
                  <el-table-column prop="failures_per_sec" label="failures/s" width="100" align="right">
                    <template #default="{row}"><span :class="row.failures_per_sec > 0 ? 'text-danger' : ''">{{ row.failures_per_sec }}</span></template>
                  </el-table-column>
                </el-table>
              </div>

              <!-- CHARTS 柱状图 (仅已完成时展示) -->
              <div v-if="(currentDetail.status === 'SUCCESS' || currentDetail.status === 'FAILED') && currentDetail.detail.stats && currentDetail.detail.stats.endpoints && currentDetail.detail.stats.endpoints.length > 0" class="detail-item">
                <span class="detail-label">CHARTS:</span>
                <div class="charts-container">
                  <!-- 响应时间对比图 -->
                  <div class="chart-box">
                    <div class="chart-title">Average Response Time (ms)</div>
                    <div class="bar-chart">
                      <div v-for="ep in currentDetail.detail.stats.endpoints" :key="ep.name" class="bar-row">
                        <div class="bar-label" :title="ep.name">{{ ep.name.length > 30 ? ep.name.slice(0, 30) + '...' : ep.name }}</div>
                        <div class="bar-track">
                          <div class="bar-fill bar-fill-primary" :style="{ width: getBarWidth(ep.avg_ms, maxAvgMs) + '%' }"></div>
                          <span class="bar-value">{{ ep.avg_ms }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <!-- 请求数对比图 -->
                  <div class="chart-box">
                    <div class="chart-title">Total Requests</div>
                    <div class="bar-chart">
                      <div v-for="ep in currentDetail.detail.stats.endpoints" :key="ep.name" class="bar-row">
                        <div class="bar-label" :title="ep.name">{{ ep.name.length > 30 ? ep.name.slice(0, 30) + '...' : ep.name }}</div>
                        <div class="bar-track">
                          <div class="bar-fill bar-fill-success" :style="{ width: getBarWidth(ep.requests, maxRequests) + '%' }"></div>
                          <span class="bar-value">{{ ep.requests }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Locust 压测脚本 & Web UI -->
              <div class="detail-item">
                <span class="detail-label">压测脚本:</span>
                <div style="margin-top:8px; display:flex; align-items:center; gap:12px; flex-wrap:wrap;">
                  <el-button v-if="currentDetail.status === 'SUCCESS' || currentDetail.status === 'FAILED'" type="success" size="small" @click="viewHistoricalResults">
                    <el-icon><TrendCharts /></el-icon> 查看结果
                  </el-button>
                  <el-button type="primary" size="small" :loading="syncLoading" @click="syncAndOpenLocust">
                    <el-icon><Link /></el-icon> 重新执行
                  </el-button>
                  <el-button size="small" @click="downloadPerfScript">
                    <el-icon><Download /></el-icon> 下载脚本
                  </el-button>
                  <el-button size="small" @click="viewPerfScript">
                    <el-icon><Document /></el-icon> 查看脚本
                  </el-button>
                </div>
                <div style="margin-top:8px; color:#909399; font-size:12px;">
                  <span v-if="currentDetail.status === 'SUCCESS' || currentDetail.status === 'FAILED'">
                    点击"查看结果"查看本次执行的详细统计 | 点击"重新执行"可重新跑一次压测
                  </span>
                  <span v-else>
                    点击"重新执行"将同步脚本到 Locust Web UI 并打开，可手动启动压测
                  </span>
                </div>
                <el-input v-if="currentDetail.detail.output" type="textarea" :model-value="currentDetail.detail.output" :rows="4" readonly style="margin-top:8px" />
              </div>
            </template>
            <template v-else>
              <el-input type="textarea" :model-value="JSON.stringify(currentDetail.detail, null, 2)" :rows="6" readonly />
            </template>
            <div v-if="currentDetail.detail.error" class="detail-item" :class="currentDetail.detail.exit_code === 1 ? 'warning-message' : 'error-message'">
              <span class="detail-label">{{ currentDetail.detail.exit_code === 1 ? '提示:' : '错误信息:' }}</span>
              <span :class="currentDetail.detail.exit_code === 1 ? 'warning-text' : 'error-text'">{{ currentDetail.detail.error }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无详情" />
        </div>
      </div>
      <div v-else v-loading="detailLoading" style="min-height: 200px;"></div>
    </el-dialog>

    <!-- 查看脚本弹窗 -->
    <el-dialog v-model="scriptDialogVisible" title="压测脚本查看" width="65%" top="5vh" destroy-on-close>
      <div v-loading="scriptLoading" style="min-height:200px;">
        <pre v-if="scriptContent" class="script-code-block"><code>{{ scriptContent }}</code></pre>
        <el-empty v-else-if="!scriptLoading" description="暂无脚本内容" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Link, Search, Download, TrendCharts } from '@element-plus/icons-vue'
import { getTaskList, getTaskCreators, deleteTask, startTask, cancelTask } from '@/api/tasks'
import type { TaskItem, TaskStatus, TaskPriority } from '@/api/tasks'
import { getResultOverview, getResultList, getResultDetail, syncPerfScript } from '@/api/results'
import type { ResultOverview, ResultItem, ResultDetail } from '@/api/results'

const loading = ref(false)
const taskList = ref<TaskItem[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const filters = reactive({ keyword: '', creator_id: '' })
const creators = ref<{ id: string; username: string }[]>([])

// 结果展示弹窗相关状态
const resultDialogVisible = ref(false)
const currentTaskId = ref('')
const currentTaskName = ref('')
const resultLoading = ref(false)
const resultOverview = ref<ResultOverview | null>(null)
const resultList = ref<ResultItem[]>([])
const resultPagination = reactive({ page: 1, pageSize: 20, total: 0 })

// 用例详情弹窗相关状态
const detailDialogVisible = ref(false)
const detailLoading = ref(false)
const currentDetail = ref<ResultDetail | null>(null)
const syncLoading = ref(false)
const scriptDialogVisible = ref(false)
const scriptContent = ref('')
const scriptLoading = ref(false)

const locustWebUrl = computed(() => {
  if (!currentDetail.value?.detail) return '#'
  const host = window.location.hostname
  const caseId = currentDetail.value.case_id
  return caseId ? `http://${host}:8089/?case_id=${caseId}` : `http://${host}:8089`
})

function formatDate(dateStr: string | null) { return dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-' }

function downloadPerfScript() {
  if (!currentDetail.value?.case_id) return
  const url = `/api/v1/results/perf-script/${currentDetail.value.case_id}`
  const a = document.createElement('a')
  a.href = url
  a.download = `locust_${currentDetail.value.case_id.slice(0, 8)}.py`
  a.click()
}

async function viewPerfScript() {
  if (!currentDetail.value?.case_id) return
  scriptDialogVisible.value = true
  scriptLoading.value = true
  scriptContent.value = ''
  try {
    const url = `/api/v1/results/perf-script/${currentDetail.value.case_id}`
    const res = await fetch(url, { headers: { Authorization: `Bearer ${localStorage.getItem('token') || ''}` } })
    if (res.ok) {
      scriptContent.value = await res.text()
    } else {
      ElMessage.error('获取脚本失败')
    }
  } catch {
    ElMessage.error('获取脚本失败')
  } finally {
    scriptLoading.value = false
  }
}

// STATISTICS 表格数据：从 endpoints 中解析 Method 和 Name
const perfTableData = computed(() => {
  const endpoints = currentDetail.value?.detail?.stats?.endpoints
  if (!endpoints) return []
  return endpoints.map((ep: any) => {
    const parts = (ep.name || '').split(' ', 2)
    const type = parts.length > 1 ? parts[0] : 'GET'
    const name = parts.length > 1 ? parts.slice(1).join(' ') : ep.name
    const duration = currentDetail.value?.detail?.duration || 1
    return {
      ...ep,
      type,
      name,
      avg_content_length: ep.avg_content_length || '-',
      failures_per_sec: ep.failures ? (ep.failures / duration).toFixed(2) : '0.00',
    }
  })
})

// CHARTS 辅助：计算柱状图最大值
const maxAvgMs = computed(() => {
  const endpoints = currentDetail.value?.detail?.stats?.endpoints
  if (!endpoints?.length) return 1
  return Math.max(...endpoints.map((ep: any) => ep.avg_ms || 0), 1)
})

const maxRequests = computed(() => {
  const endpoints = currentDetail.value?.detail?.stats?.endpoints
  if (!endpoints?.length) return 1
  return Math.max(...endpoints.map((ep: any) => ep.requests || 0), 1)
})

function getBarWidth(value: number, max: number): number {
  return max > 0 ? Math.max((value / max) * 100, 2) : 0
}

// STATISTICS 汇总行
function getPerfSummary(param: { columns: any[]; data: any[] }) {
  const { columns, data } = param
  const sums: string[] = []
  columns.forEach((col, index) => {
    if (index === 0) { sums[index] = 'Aggregated'; return }
    if (index === 1) { sums[index] = ''; return }
    const prop = col.property
    if (!prop) { sums[index] = ''; return }
    if (prop === 'type' || prop === 'name') { sums[index] = ''; return }
    if (prop === 'avg_content_length') { sums[index] = '-'; return }
    const values = data.map((item: any) => Number(item[prop]))
    const validValues = values.filter((v: number) => !isNaN(v))
    if (prop === 'rps' || prop === 'failures_per_sec') {
      sums[index] = validValues.reduce((a: number, b: number) => a + b, 0).toFixed(2)
    } else if (prop === 'median_ms' || prop === 'avg_ms') {
      sums[index] = validValues.length ? (validValues.reduce((a: number, b: number) => a + b, 0) / validValues.length).toFixed(1) : '0'
    } else if (prop === 'min_ms') {
      sums[index] = validValues.length ? Math.min(...validValues).toString() : '0'
    } else if (prop === 'max_ms') {
      sums[index] = validValues.length ? Math.max(...validValues).toString() : '0'
    } else {
      sums[index] = validValues.reduce((a: number, b: number) => a + b, 0).toString()
    }
  })
  return sums
}

async function syncAndOpenLocust() {
  if (!currentDetail.value?.case_id) return
  syncLoading.value = true
  try {
    await syncPerfScript(currentDetail.value.case_id)
    ElMessage.success('脚本已同步，正在加载到 Locust...')
    const host = window.location.hostname
    const caseId = currentDetail.value.case_id
    window.open(`http://${host}:8089/auto-load?case_id=${caseId}`, '_blank')
  } catch {
    ElMessage.error('同步脚本到 Locust 失败')
  } finally {
    syncLoading.value = false
  }
}

function viewHistoricalResults() {
  if (!currentDetail.value?.case_id) return
  const host = window.location.hostname
  const caseId = currentDetail.value.case_id
  const taskId = currentDetail.value.task_id || ''
  const token = localStorage.getItem('token') || ''
  window.open(`http://${host}:8089/historical-results?case_id=${caseId}&task_id=${taskId}&token=${token}`, '_blank')
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { page: pagination.page, pageSize: pagination.pageSize }
    if (filters.keyword) params.keyword = filters.keyword
    if (filters.creator_id) params.creator_id = filters.creator_id
    const res = await getTaskList(params)
    taskList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

async function fetchCreators() {
  try {
    const res = await getTaskCreators()
    creators.value = res.data || []
  } catch { creators.value = [] }
}

async function fetchResults() {
  if (!currentTaskId.value) return
  resultLoading.value = true
  try {
    const params: any = { taskId: currentTaskId.value, page: resultPagination.page, pageSize: resultPagination.pageSize }
    const res = await getResultList(params)
    resultList.value = res.data?.list || []
    resultPagination.total = res.data?.pagination?.total || 0
  } catch { resultList.value = [] } finally { resultLoading.value = false }
}

async function fetchOverview() {
  if (!currentTaskId.value) return
  try { const res = await getResultOverview(currentTaskId.value); resultOverview.value = res.data || null } catch { resultOverview.value = null }
}

function handleShowResult(row: TaskItem) {
  currentTaskId.value = row.id
  currentTaskName.value = row.name
  resultDialogVisible.value = true
  resultPagination.page = 1
  fetchOverview()
  fetchResults()
}

function handleCreate() { ElMessage.info('新建任务功能待实现') }
async function handleStart(row: TaskItem) { try { await startTask(row.id); ElMessage.success('任务已启动'); fetchData() } catch {} }
async function handleCancel(row: TaskItem) { try { await cancelTask(row.id); ElMessage.success('任务已取消'); fetchData() } catch {} }
async function handleDelete(id: string) { try { await deleteTask(id); ElMessage.success('删除成功'); fetchData() } catch {} }

async function handleDetail(row: ResultItem) {
  detailDialogVisible.value = true
  detailLoading.value = true
  currentDetail.value = null
  try {
    const res = await getResultDetail(row.id)
    currentDetail.value = res.data || null
  } catch {
    currentDetail.value = null
    ElMessage.error('获取详情失败')
  } finally {
    detailLoading.value = false
  }
}

onMounted(() => { fetchData(); fetchCreators() })
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
.header-actions { display:flex; align-items:center; gap:10px; }
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }

/* 结果展示弹窗样式 */
.result-dialog :deep(.el-dialog) {
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
}
.result-dialog-content { max-height:75vh; overflow-y:auto; }
.overview-row { margin-bottom:16px; padding:12px; background:linear-gradient(135deg, #f5f7fa 0%, #e4e7ed 100%); border-radius:8px; }
.overview-item { text-align:center; padding:8px 0; }
.overview-label { font-size:12px; color:#909399; margin-bottom:4px; }
.overview-value { font-size:20px; font-weight:600; color:#303133; }
.overview-item.success .overview-value { color:#67c23a; }
.overview-item.danger .overview-value { color:#f56c6c; }

/* 用例详情弹窗样式 */
.detail-dialog :deep(.el-dialog) {
  border-radius: 8px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}
.detail-content { max-height:70vh; overflow-y:auto; }
.detail-info { margin-bottom:20px; }
.detail-section { margin-top:16px; }
.detail-section h4 { margin:0 0 12px 0; padding-bottom:8px; border-bottom:2px solid #409eff; color:#303133; }
.detail-json { background:#f5f7fa; padding:16px; border-radius:6px; }
.detail-item { margin-bottom:12px; }
.detail-item:last-child { margin-bottom:0; }
.detail-label { font-weight:600; color:#606266; margin-right:8px; }
.error-output :deep(textarea) { color:#f56c6c; }
.error-message { padding:8px 12px; background:#fef0f0; border-radius:4px; border-left:3px solid #f56c6c; }
.error-text { color:#f56c6c; }
.warning-message { padding:8px 12px; background:#fdf6ec; border-radius:4px; border-left:3px solid #e6a23c; }
.warning-text { color:#e6a23c; }

/* 步骤时间轴样式 */
.step-count { margin-left:12px; color:#909399; font-size:13px; }
.steps-timeline { margin-top:12px; max-height:500px; overflow-y:auto; padding-right:8px; }
.steps-timeline::-webkit-scrollbar { width:6px; }
.steps-timeline::-webkit-scrollbar-thumb { background:#dcdfe6; border-radius:3px; }
.steps-timeline::-webkit-scrollbar-thumb:hover { background:#c0c4cc; }
.step-card { margin-bottom:0; }
.step-card :deep(.el-card__body) { padding:12px; }
.step-header { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.step-title { font-weight:600; color:#303133; }
.step-duration { margin-left:auto; color:#909399; font-size:12px; }
.step-code { background:#f5f7fa; padding:8px 12px; border-radius:4px; margin-bottom:8px; overflow-x:auto; }
.step-code code { font-family:'Courier New', Courier, monospace; font-size:13px; color:#476582; word-break:break-all; }
.step-log { display:flex; align-items:center; gap:6px; color:#606266; font-size:13px; margin-bottom:8px; padding:6px 10px; background:#f0f9eb; border-radius:4px; border-left:3px solid #67c23a; }
.step-log .el-icon { color:#67c23a; flex-shrink:0; }
.step-screenshot { border:1px solid #ebeef5; border-radius:6px; overflow:hidden; }
.step-screenshot .el-image { width:100%; max-height:300px; display:block; }
.step-screenshot .image-error { padding:20px; text-align:center; color:#c0c4cc; }

/* 性能压测结果样式 */
.perf-overview { background:#f5f7fa; border-radius:8px; padding:12px 16px; margin-bottom:16px; }
.perf-stat { text-align:left; padding:4px 0; }
.perf-stat-label { font-size:12px; color:#909399; margin-bottom:2px; }
.perf-stat-value { font-size:16px; font-weight:600; color:#303133; }
.perf-params { display:flex; flex-wrap:wrap; gap:12px; margin-top:8px; }
.perf-param-item { background:#f5f7fa; border-radius:6px; padding:10px 20px; min-width:140px; }
.perf-param-label { display:block; font-size:12px; color:#909399; margin-bottom:4px; }
.perf-param-value { display:block; font-size:15px; font-weight:600; color:#303133; }
.text-danger { color:#f56c6c; }
.text-primary { color:#409eff; }

/* CHARTS 柱状图样式 */
.charts-container { display:flex; gap:24px; margin-top:12px; }
.chart-box { flex:1; background:#f5f7fa; border-radius:8px; padding:16px; }
.chart-title { font-size:14px; font-weight:600; color:#303133; margin-bottom:12px; }
.bar-chart { display:flex; flex-direction:column; gap:10px; }
.bar-row { display:flex; align-items:center; gap:8px; }
.bar-label { width:180px; font-size:12px; color:#606266; text-align:right; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex-shrink:0; }
.bar-track { flex:1; height:22px; background:#e4e7ed; border-radius:4px; position:relative; overflow:hidden; display:flex; align-items:center; }
.bar-fill { height:100%; border-radius:4px; transition:width 0.5s ease; min-width:2px; }
.bar-fill-primary { background:linear-gradient(90deg, #409eff, #66b1ff); }
.bar-fill-success { background:linear-gradient(90deg, #67c23a, #85ce61); }
.bar-value { position:absolute; right:8px; font-size:11px; color:#303133; font-weight:600; }

/* 脚本查看弹窗样式 */
.script-code-block {
  background:#1e1e1e;
  color:#d4d4d4;
  padding:16px;
  border-radius:6px;
  overflow:auto;
  max-height:65vh;
  font-family:'Courier New', Courier, monospace;
  font-size:13px;
  line-height:1.6;
  white-space:pre;
  tab-size:4;
}
</style>
