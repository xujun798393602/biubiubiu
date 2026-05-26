<template>
  <div class="task-list">
    <el-card>
      <template #header>
        <div class="card-header"><span>任务管理</span><el-button type="primary" icon="Plus" @click="handleCreate">新建任务</el-button></div>
      </template>
      <el-table :data="taskList" v-loading="loading" stripe border>
        <el-table-column prop="name" label="任务名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='SUCCESS'?'success':row.status==='FAILED'?'danger':row.status==='RUNNING'?'warning':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
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

              <!-- 性能结果统计 -->
              <div v-if="currentDetail.detail.stats && currentDetail.detail.stats.total" class="perf-overview">
                <el-row :gutter="16">
                  <el-col :span="5"><div class="perf-stat"><div class="perf-stat-label">总请求数</div><div class="perf-stat-value">{{ currentDetail.detail.stats.total.requests }}</div></div></el-col>
                  <el-col :span="5"><div class="perf-stat"><div class="perf-stat-label">失败数</div><div class="perf-stat-value" :class="currentDetail.detail.stats.total.failures > 0 ? 'text-danger' : ''">{{ currentDetail.detail.stats.total.failures }}</div></div></el-col>
                  <el-col :span="5"><div class="perf-stat"><div class="perf-stat-label">失败率</div><div class="perf-stat-value" :class="currentDetail.detail.stats.total.failure_rate > 0 ? 'text-danger' : ''">{{ currentDetail.detail.stats.total.failure_rate }}%</div></div></el-col>
                  <el-col :span="4"><div class="perf-stat"><div class="perf-stat-label">平均响应</div><div class="perf-stat-value">{{ currentDetail.detail.stats.total.avg_ms }} ms</div></div></el-col>
                  <el-col :span="5"><div class="perf-stat"><div class="perf-stat-label">RPS</div><div class="perf-stat-value text-primary">{{ currentDetail.detail.stats.total.rps }}</div></div></el-col>
                </el-row>
              </div>

              <!-- 请求明细表格 -->
              <div v-if="currentDetail.detail.stats && currentDetail.detail.stats.endpoints && currentDetail.detail.stats.endpoints.length > 0" class="detail-item">
                <span class="detail-label">请求明细:</span>
                <el-table :data="currentDetail.detail.stats.endpoints" size="small" border style="margin-top:8px" stripe>
                  <el-table-column prop="name" label="请求名称" min-width="200" show-overflow-tooltip />
                  <el-table-column prop="requests" label="请求数" width="90" align="right" />
                  <el-table-column prop="failures" label="失败数" width="80" align="right">
                    <template #default="{row}"><span :class="row.failures > 0 ? 'text-danger' : ''">{{ row.failures }}</span></template>
                  </el-table-column>
                  <el-table-column prop="failure_rate" label="失败率" width="80" align="right">
                    <template #default="{row}"><span :class="row.failure_rate > 0 ? 'text-danger' : ''">{{ row.failure_rate }}%</span></template>
                  </el-table-column>
                  <el-table-column prop="avg_ms" label="平均(ms)" width="100" align="right" />
                  <el-table-column prop="min_ms" label="最小(ms)" width="90" align="right" />
                  <el-table-column prop="max_ms" label="最大(ms)" width="90" align="right" />
                  <el-table-column prop="median_ms" label="中位数(ms)" width="100" align="right" />
                  <el-table-column prop="rps" label="RPS" width="80" align="right" />
                </el-table>
              </div>

              <!-- Locust Web UI 跳转 -->
              <div class="detail-item">
                <span class="detail-label">Locust Web UI:</span>
                <el-link type="primary" :href="locustWebUrl" target="_blank" :underline="false">
                  <el-icon><Link /></el-icon> 打开 Locust 压测界面
                </el-link>
                <span style="color:#909399; font-size:12px; margin-left:8px">需先启动 locust-web 服务: docker compose -f docker-compose.worker.yml up -d locust-web</span>
              </div>

              <!-- 原始输出 -->
              <div v-if="currentDetail.detail.output" class="detail-item">
                <span class="detail-label">原始输出:</span>
                <el-input type="textarea" :model-value="currentDetail.detail.output" :rows="8" readonly />
              </div>
            </template>
            <template v-else>
              <el-input type="textarea" :model-value="JSON.stringify(currentDetail.detail, null, 2)" :rows="6" readonly />
            </template>
            <div v-if="currentDetail.detail.error" class="detail-item error-message">
              <span class="detail-label">错误信息:</span>
              <span class="error-text">{{ currentDetail.detail.error }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无详情" />
        </div>
      </div>
      <div v-else v-loading="detailLoading" style="min-height: 200px;"></div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Document, Link } from '@element-plus/icons-vue'
import { getTaskList, deleteTask, startTask, cancelTask } from '@/api/tasks'
import type { TaskItem, TaskStatus, TaskPriority } from '@/api/tasks'
import { getResultOverview, getResultList, getResultDetail } from '@/api/results'
import type { ResultOverview, ResultItem, ResultDetail } from '@/api/results'

const loading = ref(false)
const taskList = ref<TaskItem[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

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

const locustWebUrl = computed(() => {
  if (!currentDetail.value?.detail) return '#'
  const host = window.location.hostname
  return `http://${host}:8089`
})

function formatDate(dateStr: string | null) { return dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-' }

async function fetchData() {
  loading.value = true
  try {
    const res = await getTaskList({ page: pagination.page, pageSize: pagination.pageSize })
    taskList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
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

onMounted(fetchData)
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
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
</style>
