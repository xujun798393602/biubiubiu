<template>
  <div class="node-list">
    <!-- Stats Cards -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.online_nodes }}</div>
            <div class="stat-label">在线节点</div>
          </div>
          <el-icon class="stat-icon" color="#67c23a"><CircleCheck /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.by_type?.PLAYWRIGHT || 0 }}</div>
            <div class="stat-label">Playwright 节点</div>
          </div>
          <el-icon class="stat-icon" color="#409eff"><Monitor /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.by_type?.LOCUST || 0 }}</div>
            <div class="stat-label">Locust 节点</div>
          </div>
          <el-icon class="stat-icon" color="#e6a23c"><DataLine /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_tasks_running }}</div>
            <div class="stat-label">运行中任务</div>
          </div>
          <el-icon class="stat-icon" color="#909399"><Operation /></el-icon>
        </el-card>
      </el-col>
    </el-row>

    <!-- Main Card -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>节点管理</span>
          <div class="header-actions">
            <el-button-group>
              <el-button type="primary" @click="handleScalePlaywright">
                <el-icon><Plus /></el-icon>
                Playwright +1
              </el-button>
              <el-button type="warning" @click="handleScaleLocust">
                <el-icon><Plus /></el-icon>
                Locust +1
              </el-button>
            </el-button-group>
            <el-button type="success" icon="Plus" @click="handleCreate">添加节点</el-button>
          </div>
        </div>
      </template>

      <!-- Filter Bar -->
      <div class="filter-bar">
        <el-select v-model="filters.status" placeholder="状态筛选" clearable style="width: 120px">
          <el-option label="在线" value="ONLINE" />
          <el-option label="离线" value="OFFLINE" />
          <el-option label="忙碌" value="BUSY" />
          <el-option label="错误" value="ERROR" />
        </el-select>
        <el-select v-model="filters.node_type" placeholder="类型筛选" clearable style="width: 140px">
          <el-option label="Playwright" value="PLAYWRIGHT" />
          <el-option label="Locust" value="LOCUST" />
          <el-option label="混合" value="MIXED" />
        </el-select>
        <el-input v-model="filters.keyword" placeholder="搜索节点名称" clearable style="width: 200px" />
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>

      <!-- Node Table -->
      <el-table :data="nodeList" v-loading="loading" stripe border>
        <el-table-column prop="name" label="节点名称" min-width="150" />
        <el-table-column prop="host" label="地址" min-width="160" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="node_type" label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getNodeTypeTag(row.node_type)" size="small">
              {{ row.node_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="负载" width="150">
          <template #default="{ row }">
            <div class="load-info">
              <span>{{ row.current_tasks }}/{{ row.max_concurrent }}</span>
              <el-progress
                :percentage="(row.current_tasks / row.max_concurrent) * 100"
                :stroke-width="4"
                :show-text="false"
                :status="row.current_tasks >= row.max_concurrent ? 'exception' : ''"
              />
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="cpu_usage" label="CPU" width="80">
          <template #default="{ row }">{{ row.cpu_usage ?? '-' }}%</template>
        </el-table-column>
        <el-table-column prop="memory_usage" label="内存" width="80">
          <template #default="{ row }">{{ row.memory_usage ?? '-' }}%</template>
        </el-table-column>
        <el-table-column prop="agent_version" label="版本" width="80" />
        <el-table-column label="最后心跳" width="160">
          <template #default="{ row }">
            {{ row.last_heartbeat_at ? formatTime(row.last_heartbeat_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="success" size="small" @click="handleApiKey(row)">密钥</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)">
              <template #reference>
                <el-button text type="danger" size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        class="pagination"
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchData"
        @current-change="fetchData"
      />
    </el-card>

    <!-- Create/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑节点' : '添加节点'"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="节点名称" required>
          <el-input v-model="formData.name" placeholder="输入节点名称" />
        </el-form-item>
        <el-form-item label="节点类型" required>
          <el-select v-model="formData.node_type" style="width: 100%">
            <el-option label="Playwright (UI测试)" value="PLAYWRIGHT" />
            <el-option label="Locust (性能测试)" value="LOCUST" />
            <el-option label="混合 (支持所有类型)" value="MIXED" />
          </el-select>
        </el-form-item>
        <el-form-item label="节点地址" required>
          <el-input v-model="formData.host" placeholder="输入IP地址或主机名" />
        </el-form-item>
        <el-form-item label="节点端口">
          <el-input-number v-model="formData.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="最大并发">
          <el-input-number v-model="formData.max_concurrent" :min="1" :max="100" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '更新' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- API Key Dialog -->
    <el-dialog v-model="apiKeyDialogVisible" title="节点 API Key" width="550px">
      <div class="api-key-content">
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            <span>API Key 用于 Worker 节点认证，请妥善保管</span>
          </template>
        </el-alert>
        <div class="api-key-value">
          <el-input
            ref="apiKeyInputRef"
            v-model="displayApiKey"
            readonly
            type="textarea"
            :rows="3"
            :autosize="{ minRows: 2, maxRows: 4 }"
            :class="{ 'api-key-cipher': !showApiKeyPlain, 'api-key-empty': !hasValidApiKey }"
            @click="handleApiKeyClick"
          />
          <div class="api-key-hint">
            <template v-if="!hasValidApiKey">
              未保存 API Key，请点击"重新生成"按钮生成新的 Key
            </template>
            <template v-else>
              {{ showApiKeyPlain ? '明文模式：点击文本框可全选，支持 Ctrl+C 复制' : '密文模式：仅支持按钮复制' }}
            </template>
          </div>
        </div>
        <div class="api-key-actions">
          <el-button @click="toggleApiKeyVisibility" :disabled="!hasValidApiKey">
            <el-icon>
              <View v-if="!showApiKeyPlain" />
              <Hide v-else />
            </el-icon>
            {{ showApiKeyPlain ? '隐藏' : '显示' }}
          </el-button>
          <el-button type="primary" @click="copyApiKey" :disabled="!hasValidApiKey">
            <el-icon><DocumentCopy /></el-icon>
            复制到剪贴板
          </el-button>
          <el-button type="danger" @click="handleRegenerateApiKey" :loading="regenerating">
            重新生成
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- Scale Dialog -->
    <el-dialog v-model="scaleDialogVisible" :title="`扩容 ${scaleType} 节点`" width="500px">
      <el-form :model="scaleForm" label-width="100px">
        <el-form-item label="节点名称">
          <el-input v-model="scaleForm.name" :placeholder="`${scaleType}-worker`" />
        </el-form-item>
        <el-form-item label="节点地址">
          <el-input v-model="scaleForm.host" placeholder="输入IP地址或主机名" />
        </el-form-item>
        <el-form-item label="节点端口">
          <el-input-number v-model="scaleForm.port" :min="1" :max="65535" />
        </el-form-item>
        <el-form-item label="最大并发">
          <el-input-number v-model="scaleForm.max_concurrent" :min="1" :max="100" />
        </el-form-item>
        <el-form-item label="扩容数量">
          <el-input-number v-model="scaleForm.count" :min="1" :max="10" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="scaleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleScaleSubmit" :loading="scaling">
          扩容
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  CircleCheck, Monitor, DataLine, Operation, Plus, DocumentCopy, View, Hide
} from '@element-plus/icons-vue'
import {
  getNodeList, deleteNode, createNode, updateNode, getNodeStats,
  scaleNodes, regenerateApiKey,
  type NodeItem, type NodeStats as NodeStatsType, type NodeType
} from '@/api/nodes'

const loading = ref(false)
const nodeList = ref<NodeItem[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const filters = reactive({ status: '', node_type: '', keyword: '' })

const stats = reactive<NodeStatsType>({
  total_nodes: 0,
  online_nodes: 0,
  offline_nodes: 0,
  busy_nodes: 0,
  error_nodes: 0,
  by_type: {},
  total_tasks_running: 0,
  total_max_concurrent: 0,
  queue_depth: {},
})

// Dialog state
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref('')
const submitting = ref(false)
const formData = reactive({
  name: '',
  node_type: 'MIXED' as NodeType,
  host: '',
  port: 8080,
  max_concurrent: 5,
})

// API Key dialog
const apiKeyDialogVisible = ref(false)
const currentApiKey = ref('')
const currentApiKeyId = ref('')
const regenerating = ref(false)
const apiKeyInputRef = ref<any>(null)
const showApiKeyPlain = ref(false)
const maskedApiKey = ref('')

// 计算显示的 API Key
const displayApiKey = computed(() => {
  if (!currentApiKey.value && !maskedApiKey.value) {
    return '暂无 API Key，请点击"重新生成"按钮生成'
  }
  return showApiKeyPlain.value ? currentApiKey.value : maskedApiKey.value
})

// 判断是否有有效的 API Key
const hasValidApiKey = computed(() => {
  return !!currentApiKey.value || !!getApiKeyFromStorage(currentApiKeyId.value)
})

// API Key 本地存储
const API_KEY_STORAGE_KEY = 'node_api_keys'

function saveApiKeyToStorage(nodeId: string, apiKey: string) {
  try {
    const stored = localStorage.getItem(API_KEY_STORAGE_KEY)
    const keys = stored ? JSON.parse(stored) : {}
    keys[nodeId] = apiKey
    localStorage.setItem(API_KEY_STORAGE_KEY, JSON.stringify(keys))
  } catch (e) {
    console.warn('Failed to save API key to storage:', e)
  }
}

function getApiKeyFromStorage(nodeId: string): string | null {
  try {
    const stored = localStorage.getItem(API_KEY_STORAGE_KEY)
    if (!stored) return null
    const keys = JSON.parse(stored)
    return keys[nodeId] || null
  } catch (e) {
    return null
  }
}

function removeApiKeyFromStorage(nodeId: string) {
  try {
    const stored = localStorage.getItem(API_KEY_STORAGE_KEY)
    if (!stored) return
    const keys = JSON.parse(stored)
    delete keys[nodeId]
    localStorage.setItem(API_KEY_STORAGE_KEY, JSON.stringify(keys))
  } catch (e) {
    console.warn('Failed to remove API key from storage:', e)
  }
}

// Scale dialog
const scaleDialogVisible = ref(false)
const scaleType = ref<NodeType>('PLAYWRIGHT')
const scaling = ref(false)
const scaleForm = reactive({
  name: '',
  host: '',
  port: 8080,
  max_concurrent: 3,
  count: 1,
})

let refreshTimer: ReturnType<typeof setInterval> | null = null

async function fetchData() {
  loading.value = true
  try {
    const res = await getNodeList({
      page: pagination.page,
      pageSize: pagination.pageSize,
      status: filters.status || undefined,
      node_type: filters.node_type || undefined,
      keyword: filters.keyword || undefined,
    })
    nodeList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally {
    loading.value = false
  }
}

async function fetchStats() {
  try {
    const res = await getNodeStats()
    if (res.data) {
      Object.assign(stats, res.data)
    }
  } catch {}
}

function handleCreate() {
  isEdit.value = false
  editId.value = ''
  formData.name = ''
  formData.node_type = 'MIXED'
  formData.host = ''
  formData.port = 8080
  formData.max_concurrent = 5
  dialogVisible.value = true
}

function handleEdit(row: NodeItem) {
  isEdit.value = true
  editId.value = row.id
  formData.name = row.name
  formData.node_type = row.node_type as NodeType
  formData.host = row.host
  formData.port = row.port
  formData.max_concurrent = row.max_concurrent
  dialogVisible.value = true
}

async function handleSubmit() {
  submitting.value = true
  try {
    if (isEdit.value) {
      await updateNode(editId.value, formData)
      ElMessage.success('更新成功')
    } else {
      const res = await createNode(formData)
      ElMessage.success('创建成功')
      if (res.data?.api_key) {
        currentApiKey.value = res.data.api_key
        maskedApiKey.value = generateMaskedKey(res.data.api_key)
        showApiKeyPlain.value = true  // 创建后默认显示明文
        // 保存到本地存储
        saveApiKeyToStorage(res.data.id, res.data.api_key)
        apiKeyDialogVisible.value = true
      }
    }
    dialogVisible.value = false
    fetchData()
    fetchStats()
  } catch {} finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await deleteNode(id)
    // 从本地存储中删除 API Key
    removeApiKeyFromStorage(id)
    ElMessage.success('删除成功')
    fetchData()
    fetchStats()
  } catch {}
}

function handleApiKey(row: NodeItem) {
  currentApiKeyId.value = row.id

  // 尝试从本地存储获取 API Key
  const storedKey = getApiKeyFromStorage(row.id)

  if (storedKey) {
    currentApiKey.value = storedKey
    maskedApiKey.value = generateMaskedKey(storedKey)
    showApiKeyPlain.value = false  // 默认显示密文
  } else {
    // 没有存储的 API Key，提示用户重新生成
    currentApiKey.value = ''
    maskedApiKey.value = ''
    showApiKeyPlain.value = false
  }

  apiKeyDialogVisible.value = true
}

async function handleRegenerateApiKey() {
  regenerating.value = true
  try {
    const res = await regenerateApiKey(currentApiKeyId.value)
    if (res.data?.api_key) {
      currentApiKey.value = res.data.api_key
      maskedApiKey.value = generateMaskedKey(res.data.api_key)
      showApiKeyPlain.value = true  // 生成后默认显示明文
      // 保存到本地存储
      saveApiKeyToStorage(currentApiKeyId.value, res.data.api_key)
      ElMessage.success('API Key 已重新生成')
    }
  } catch {} finally {
    regenerating.value = false
  }
}

function selectApiKey() {
  // 点击时全选文本
  if (apiKeyInputRef.value) {
    const textarea = apiKeyInputRef.value.$el.querySelector('textarea')
    if (textarea) {
      textarea.select()
    }
  }
}

function toggleApiKeyVisibility() {
  showApiKeyPlain.value = !showApiKeyPlain.value
}

function generateMaskedKey(key: string) {
  // 生成密文，保留前6位和后4位
  if (!key || key.length <= 10) return '••••••••••••••••••••'
  const prefix = key.substring(0, 6)
  const suffix = key.substring(key.length - 4)
  const masked = '•'.repeat(Math.max(20, key.length - 10))
  return `${prefix}${masked}${suffix}`
}

function handleApiKeyClick() {
  // 只有在明文模式下才允许选择
  if (showApiKeyPlain.value) {
    selectApiKey()
  }
}

function copyApiKey() {
  // 尝试使用现代 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(currentApiKey.value).then(() => {
      ElMessage.success('已复制到剪贴板')
    }).catch(() => {
      fallbackCopy()
    })
  } else {
    fallbackCopy()
  }
}

function fallbackCopy() {
  // 降级方案：使用 textarea + execCommand
  const textarea = document.createElement('textarea')
  textarea.value = currentApiKey.value
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  textarea.style.top = '-9999px'
  document.body.appendChild(textarea)
  textarea.focus()
  textarea.select()
  try {
    const success = document.execCommand('copy')
    if (success) {
      ElMessage.success('已复制到剪贴板')
    } else {
      ElMessage.warning('复制失败，请手动复制')
    }
  } catch (err) {
    ElMessage.warning('复制失败，请手动复制')
  } finally {
    document.body.removeChild(textarea)
  }
}

function handleScalePlaywright() {
  scaleType.value = 'PLAYWRIGHT'
  scaleForm.name = 'playwright-worker'
  scaleForm.max_concurrent = 3
  scaleDialogVisible.value = true
}

function handleScaleLocust() {
  scaleType.value = 'LOCUST'
  scaleForm.name = 'locust-worker'
  scaleForm.max_concurrent = 5
  scaleDialogVisible.value = true
}

async function handleScaleSubmit() {
  scaling.value = true
  try {
    const res = await scaleNodes({
      ...scaleForm,
      node_type: scaleType.value,
    })
    ElMessage.success(res.data?.message || '扩容成功')
    scaleDialogVisible.value = false
    fetchData()
    fetchStats()
  } catch {} finally {
    scaling.value = false
  }
}

function getNodeTypeTag(type: string) {
  switch (type) {
    case 'PLAYWRIGHT': return 'primary'
    case 'LOCUST': return 'warning'
    case 'MIXED': return 'success'
    default: return 'info'
  }
}

function getStatusTag(status: string) {
  switch (status) {
    case 'ONLINE': return 'success'
    case 'ERROR': return 'danger'
    case 'BUSY': return 'warning'
    default: return 'info'
  }
}

function formatTime(time: string) {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  fetchData()
  fetchStats()
  // Auto refresh every 10 seconds
  refreshTimer = setInterval(() => {
    fetchData()
    fetchStats()
  }, 10000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 16px;
}

.stat-card {
  display: flex;
  align-items: center;
}

.stat-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 20px;
}

.stat-content {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.stat-icon {
  font-size: 48px;
  opacity: 0.8;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}

.load-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.load-info span {
  font-size: 12px;
  color: #606266;
}

.api-key-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.api-key-value {
  margin-top: 8px;
}

.api-key-hint {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.api-key-value :deep(textarea) {
  font-family: 'Courier New', Courier, monospace;
  cursor: text;
}

.api-key-value :deep(.api-key-cipher textarea) {
  cursor: default;
  user-select: none;
  -webkit-user-select: none;
  color: #909399;
}

.api-key-value :deep(.api-key-empty textarea) {
  cursor: default;
  user-select: none;
  -webkit-user-select: none;
  color: #c0c4cc;
  font-style: italic;
}

.api-key-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
