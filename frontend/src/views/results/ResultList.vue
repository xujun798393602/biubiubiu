<template>
  <div class="result-list">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>结果展示</span>
          <div class="header-actions">
            <el-button icon="Download" @click="handleExport" :disabled="!taskId">导出报告</el-button>
            <el-button icon="Share" @click="handleShare" :disabled="!taskId">分享</el-button>
          </div>
        </div>
      </template>

      <el-row v-if="overview" :gutter="20" class="overview-row">
        <el-col :span="6"><div class="overview-item"><div class="overview-label">总用例数</div><div class="overview-value">{{ overview.totalCases }}</div></div></el-col>
        <el-col :span="6"><div class="overview-item success"><div class="overview-label">通过</div><div class="overview-value">{{ overview.successCount }}</div></div></el-col>
        <el-col :span="6"><div class="overview-item danger"><div class="overview-label">失败</div><div class="overview-value">{{ overview.failedCount }}</div></div></el-col>
        <el-col :span="6"><div class="overview-item"><div class="overview-label">通过率</div><div class="overview-value">{{ overview.successRate }}%</div></div></el-col>
      </el-row>

      <el-form :inline="true" class="filter-form" v-if="taskId">
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部" clearable @change="fetchResults">
            <el-option label="通过" value="SUCCESS" /><el-option label="失败" value="FAILED" /><el-option label="跳过" value="SKIPPED" />
          </el-select>
        </el-form-item>
      </el-form>

      <el-empty v-if="!taskId" description="请从任务管理页面选择任务查看结果">
        <el-button type="primary" @click="router.push('/tasks')">前往任务管理</el-button>
      </el-empty>

      <el-table v-else :data="resultList" v-loading="loading" stripe border>
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

      <el-pagination v-if="taskId" class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next, jumper" @size-change="fetchResults" @current-change="fetchResults" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getResultOverview, getResultList, exportResults, createShareLink } from '@/api/results'
import type { ResultOverview, ResultItem, ResultStatus } from '@/api/results'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const taskId = ref<string>((route.query.taskId as string) || '')
const overview = ref<ResultOverview | null>(null)
const resultList = ref<ResultItem[]>([])
const filters = reactive({ status: '' as ResultStatus | '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

function formatDate(dateStr: string | null) { return dateStr ? new Date(dateStr).toLocaleString('zh-CN') : '-' }

async function fetchOverview() {
  if (!taskId.value) return
  try { const res = await getResultOverview(taskId.value); overview.value = res.data || null } catch { overview.value = null }
}

async function fetchResults() {
  if (!taskId.value) return
  loading.value = true
  try {
    const params: any = { taskId: taskId.value, page: pagination.page, pageSize: pagination.pageSize }
    if (filters.status) params.status = filters.status
    const res = await getResultList(params)
    resultList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch { resultList.value = [] } finally { loading.value = false }
}

async function handleExport() { try { await exportResults(taskId.value, 'EXCEL'); ElMessage.success('导出成功') } catch {} }
async function handleShare() { try { const res = await createShareLink(taskId.value, { expiresIn: '7d' }); ElMessage.success(`分享链接: ${res.data?.url}`) } catch {} }
function handleDetail(row: ResultItem) { ElMessage.info(`查看结果详情: ${row.caseName}`) }

watch(() => route.query.taskId, (val) => { taskId.value = (val as string) || ''; if (taskId.value) { fetchOverview(); fetchResults() } })
onMounted(() => { if (taskId.value) { fetchOverview(); fetchResults() } })
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
.header-actions { display:flex; gap:8px; }
.overview-row { margin-bottom:20px; padding:16px; background:#f5f7fa; border-radius:8px; }
.overview-item { text-align:center; }
.overview-label { font-size:14px; color:#909399; margin-bottom:8px; }
.overview-value { font-size:24px; font-weight:600; color:#303133; }
.overview-item.success .overview-value { color:#67c23a; }
.overview-item.danger .overview-value { color:#f56c6c; }
.filter-form { margin-bottom:16px; }
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }
</style>
