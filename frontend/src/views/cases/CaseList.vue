<template>
  <div class="case-list">
    <el-card>
      <template #header>
        <div class="card-header"><span>用例管理</span><div><el-button type="warning" icon="CaretRight" :disabled="!selectedCases.length" @click="handleBatchExecute">批量执行({{ selectedCases.length }})</el-button><el-button type="success" icon="VideoCamera" @click="showRecordDialog">用例录制</el-button><el-button type="primary" icon="Plus" @click="handleCreate">新建用例</el-button></div></div>
      </template>
      <el-form :inline="true" class="filter-form">
        <el-form-item label="类型"><el-select v-model="filters.type" style="width:140px" clearable placeholder="全部" @change="fetchData"><el-option label="API" value="API" /><el-option label="UI" value="UI" /><el-option label="性能" value="PERFORMANCE" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="filters.status" style="width:140px" clearable placeholder="全部" @change="fetchData"><el-option label="草稿" value="DRAFT" /><el-option label="激活" value="ACTIVE" /><el-option label="废弃" value="DEPRECATED" /></el-select></el-form-item>
        <el-form-item label="优先级"><el-select v-model="filters.priority" style="width:140px" clearable placeholder="全部" @change="fetchData"><el-option label="BVT" value="BVT" /><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
        <el-form-item label="编写人"><el-select v-model="filters.author" style="width:140px" clearable placeholder="全部" @change="fetchData"><el-option v-for="a in authorList" :key="a" :label="a" :value="a" /></el-select></el-form-item>
        <el-form-item label="搜索"><el-input v-model="filters.keyword" placeholder="用例名称/ID" clearable @clear="fetchData" /></el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
      <el-table :data="caseList" v-loading="loading" stripe border @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="用例ID" width="280" show-overflow-tooltip />
        <el-table-column prop="name" label="用例名称" min-width="200" show-overflow-tooltip />
        <el-table-column prop="type" label="类型" width="100"><template #default="{row}"><el-tag size="small">{{ row.type }}</el-tag></template></el-table-column>
        <el-table-column prop="priority" label="优先级" width="80"><template #default="{row}"><el-tag :type="row.priority==='BVT'?'danger':row.priority==='P0'?'danger':row.priority==='P1'?'warning':''" size="small">{{ row.priority }}</el-tag></template></el-table-column>
        <el-table-column prop="author" label="编写人" width="100" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='ACTIVE'?'success':row.status==='DEPRECATED'?'info':''" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{row}">
            <el-button text type="success" size="small" @click="handleExecute(row)">执行</el-button>
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10,20,50]" layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
    </el-card>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用例' : '新建用例'" width="780px" destroy-on-close draggable>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-tabs v-model="activeTab">
          <!-- Basic Info Tab -->
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="用例ID" v-if="isEdit"><el-input :model-value="editingId" disabled /></el-form-item>
            <el-form-item label="用例名称" prop="name"><el-input v-model="form.name" placeholder="请输入用例名称" /></el-form-item>
            <el-form-item label="用例类型" prop="type"><el-select v-model="form.type" placeholder="请选择类型" @change="onTypeChange"><el-option label="API" value="API" /><el-option label="UI" value="UI" /><el-option label="性能测试" value="PERFORMANCE" /></el-select></el-form-item>
            <el-form-item label="优先级"><el-select v-model="form.priority"><el-option label="BVT" value="BVT" /><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
            <el-form-item label="编写人"><el-input v-model="form.author" placeholder="用例编写人" /></el-form-item>
            <el-form-item label="所属模块"><el-input v-model="form.module" placeholder="所属模块" /></el-form-item>
            <el-form-item label="标签"><el-select v-model="form.tags" multiple filterable allow-create placeholder="输入标签后回车" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
          </el-tab-pane>

          <!-- Steps Tab -->
          <el-tab-pane label="操作步骤" name="steps">
            <el-form-item label="前置条件"><el-input v-model="form.preconditions" type="textarea" :rows="3" placeholder="执行用例前需要满足的前置条件" /></el-form-item>
            <el-form-item label="操作步骤"><el-input v-model="form.stepsText" type="textarea" :rows="6" placeholder="描述具体的操作步骤" /></el-form-item>
            <el-form-item label="预期结果"><el-input v-model="form.expected_result" type="textarea" :rows="2" placeholder="总体预期结果" /></el-form-item>
            <el-form-item label="后置条件"><el-input v-model="form.postconditions" type="textarea" :rows="3" placeholder="用例执行完成后的后置条件" /></el-form-item>
          </el-tab-pane>

          <!-- API Tab -->
          <el-tab-pane label="接口配置" name="api" v-if="form.type === 'API'">
            <el-form-item label="接口地址"><el-input v-model="form.api_url" placeholder="http://example.com/api/v1/xxx" /></el-form-item>
            <el-form-item label="请求方法"><el-select v-model="form.api_method"><el-option label="GET" value="GET" /><el-option label="POST" value="POST" /><el-option label="PUT" value="PUT" /><el-option label="DELETE" value="DELETE" /><el-option label="PATCH" value="PATCH" /></el-select></el-form-item>
            <el-form-item label="请求头"><el-input v-model="apiHeadersStr" type="textarea" :rows="3" placeholder='{"Content-Type": "application/json"}' /></el-form-item>
            <el-form-item label="请求体类型"><el-select v-model="form.api_body_type"><el-option label="JSON" value="JSON" /><el-option label="FORM" value="FORM" /><el-option label="XML" value="XML" /><el-option label="RAW" value="RAW" /><el-option label="NONE" value="NONE" /></el-select></el-form-item>
            <el-form-item label="请求体"><el-input v-model="form.api_body" type="textarea" :rows="4" placeholder="请求体内容" /></el-form-item>
            <el-form-item label="超时(ms)"><el-input-number v-model="form.api_timeout" :min="1000" :max="300000" :step="1000" /></el-form-item>
          </el-tab-pane>

          <!-- UI Tab -->
          <el-tab-pane label="UI配置" name="ui" v-if="form.type === 'UI'">
            <el-form-item label="页面地址"><el-input v-model="form.ui_url" placeholder="http://example.com/page" /></el-form-item>
            <el-form-item label="脚本类型"><el-select v-model="form.ui_script_type"><el-option label="手动" value="MANUAL" /><el-option label="Playwright" value="PLAYWRIGHT" /><el-option label="Selenium" value="SELENIUM" /></el-select></el-form-item>
            <el-form-item label="自动化脚本"><el-input v-model="form.ui_script" type="textarea" :rows="6" placeholder="自动化脚本内容" /></el-form-item>
          </el-tab-pane>

          <!-- Performance Tab -->
          <el-tab-pane label="性能配置" name="perf" v-if="form.type === 'PERFORMANCE'">
            <el-form-item label="压测地址"><el-input v-model="form.perf_url" placeholder="http://example.com/api/v1/xxx" /></el-form-item>
            <el-form-item label="并发用户数"><el-input-number v-model="form.perf_vusers" :min="1" :max="10000" /></el-form-item>
            <el-form-item label="每秒启动用户"><el-input-number v-model="form.perf_spawn_rate" :min="1" :max="1000" /></el-form-item>
            <el-form-item label="持续时间(秒)"><el-input-number v-model="form.perf_duration" :min="1" :max="36000" /></el-form-item>
          </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- Record Dialog -->
    <el-dialog v-model="recordDialogVisible" title="用例录制" width="600px" draggable destroy-on-close>
      <div class="record-panel">
        <div v-if="!recording && !recordedScript" class="record-start">
          <p>点击开始录制，将捕获浏览器操作并生成自动化脚本。</p>
          <el-button type="danger" size="large" icon="VideoCamera" @click="startRecording">开始录制</el-button>
        </div>
        <div v-if="recording" class="record-active">
          <div class="record-indicator">
            <span class="record-dot"></span>
            <span>录制中...</span>
          </div>
          <p>正在捕获浏览器操作，请在目标页面上执行操作。</p>
          <el-button type="info" size="large" icon="VideoPause" @click="stopRecording">停止录制</el-button>
        </div>
        <div v-if="recordedScript && !recording" class="record-done">
          <el-form-item label="绑定用例">
            <el-select v-model="recordBindCaseId" placeholder="选择要绑定的用例" filterable style="width:100%">
              <el-option v-for="c in caseList" :key="c.id" :label="`${c.name} (${c.id.slice(0,8)}...)`" :value="c.id" />
            </el-select>
          </el-form-item>
          <el-form-item label="录制脚本">
            <el-input v-model="recordedScript" type="textarea" :rows="10" readonly />
          </el-form-item>
        </div>
      </div>
      <template #footer>
        <el-button @click="recordDialogVisible = false">取消</el-button>
        <el-button v-if="recordedScript && !recording" type="primary" :disabled="!recordBindCaseId" @click="bindRecordedScript">绑定到用例</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { getCaseList, createCase, updateCase, getCaseDetail, deleteCase, getCaseAuthors, executeCases } from '@/api/cases'

const loading = ref(false)
const caseList = ref<any[]>([])
const authorList = ref<string[]>([])
const selectedCases = ref<any[]>([])
const filters = reactive({ type: '', status: '', priority: '', author: '', keyword: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// Current user for default author
const currentUser = (() => { try { return JSON.parse(localStorage.getItem('user') || '{}') } catch { return {} } })()

// Dialog state
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref('')
const submitting = ref(false)
const formRef = ref<FormInstance>()
const activeTab = ref('basic')

// Record dialog state
const recordDialogVisible = ref(false)
const recording = ref(false)
const recordedScript = ref('')
const recordBindCaseId = ref('')

const defaultForm = () => ({
  name: '',
  type: 'API' as string,
  priority: 'P2',
  author: currentUser?.real_name || currentUser?.username || '',
  module: '',
  tags: [] as string[],
  description: '',
  preconditions: '',
  stepsText: '',
  postconditions: '',
  expected_result: '',
  // API fields
  api_url: '',
  api_method: 'GET',
  api_headers: null as Record<string, string> | null,
  api_body_type: 'JSON',
  api_body: '',
  api_timeout: 30000,
  api_assertions: [] as any[],
  // UI fields
  ui_url: '',
  ui_script: '',
  ui_script_type: 'MANUAL',
  // Performance fields
  perf_url: '',
  perf_vusers: 10,
  perf_spawn_rate: 1,
  perf_duration: 60,
  perf_assertions: [] as any[],
})

const form = reactive(defaultForm())

const apiHeadersStr = computed({
  get: () => form.api_headers ? JSON.stringify(form.api_headers, null, 2) : '',
  set: (val: string) => {
    try { form.api_headers = val ? JSON.parse(val) : null } catch {}
  }
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入用例名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择用例类型', trigger: 'change' }],
}

function onTypeChange() {
  activeTab.value = form.type === 'API' ? 'api' : form.type === 'UI' ? 'ui' : form.type === 'PERFORMANCE' ? 'perf' : 'basic'
}

function resetForm() {
  Object.assign(form, defaultForm())
  activeTab.value = 'basic'
  editingId.value = ''
  isEdit.value = false
}

function handleCreate() {
  resetForm()
  dialogVisible.value = true
}

async function handleEdit(row: any) {
  resetForm()
  isEdit.value = true
  editingId.value = row.id
  try {
    const res = await getCaseDetail(row.id)
    const data = res.data
    Object.assign(form, {
      name: data.name || '',
      type: data.type || 'API',
      priority: data.priority || 'P2',
      author: data.author || '',
      module: data.module || '',
      tags: data.tags || [],
      description: data.description || '',
      preconditions: data.preconditions || '',
      stepsText: (data.steps && data.steps.length) ? data.steps.map((s: any) => s.action || s).join('\n') : '',
      postconditions: data.postconditions || '',
      expected_result: data.expected_result || '',
      api_url: data.api_url || '',
      api_method: data.api_method || 'GET',
      api_headers: data.api_headers || null,
      api_body_type: data.api_body_type || 'JSON',
      api_body: data.api_body || '',
      api_timeout: data.api_timeout || 30000,
      ui_url: data.ui_url || '',
      ui_script: data.ui_script || '',
      ui_script_type: data.ui_script_type || 'MANUAL',
      perf_url: data.perf_url || '',
      perf_vusers: data.perf_vusers || 10,
      perf_spawn_rate: data.perf_spawn_rate || 1,
      perf_duration: data.perf_duration || 60,
    })
    dialogVisible.value = true
  } catch {}
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    const payload: any = {
      name: form.name,
      type: form.type,
      priority: form.priority,
      author: form.author || undefined,
      module: form.module || undefined,
      tags: form.tags.length ? form.tags : undefined,
      description: form.description || undefined,
      preconditions: form.preconditions || undefined,
      steps: form.stepsText ? [{ action: form.stepsText }] : undefined,
      postconditions: form.postconditions || undefined,
      expected_result: form.expected_result || undefined,
    }

    if (form.type === 'API') {
      payload.api_url = form.api_url || undefined
      payload.api_method = form.api_method || undefined
      payload.api_headers = form.api_headers || undefined
      payload.api_body_type = form.api_body_type || undefined
      payload.api_body = form.api_body || undefined
      payload.api_timeout = form.api_timeout || undefined
    } else if (form.type === 'UI') {
      payload.ui_url = form.ui_url || undefined
      payload.ui_script = form.ui_script || undefined
      payload.ui_script_type = form.ui_script_type || undefined
    } else if (form.type === 'PERFORMANCE') {
      payload.perf_url = form.perf_url || undefined
      payload.perf_vusers = form.perf_vusers || undefined
      payload.perf_spawn_rate = form.perf_spawn_rate || undefined
      payload.perf_duration = form.perf_duration || undefined
    }

    if (isEdit.value) {
      await updateCase(editingId.value, payload)
      ElMessage.success('更新成功')
    } else {
      await createCase(payload)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchData()
  } catch {} finally { submitting.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const res = await getCaseList({ ...filters, page: pagination.page, pageSize: pagination.pageSize })
    caseList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

async function fetchAuthors() {
  try {
    const res = await getCaseAuthors()
    authorList.value = res.data || []
  } catch {}
}

async function handleDelete(id: string) {
  try { await deleteCase(id); ElMessage.success('删除成功'); fetchData() } catch {}
}

// Execution functions
function handleSelectionChange(selection: any[]) {
  selectedCases.value = selection
}

async function handleExecute(row: any) {
  try {
    await ElMessageBox.confirm(`确认执行用例"${row.name}"？`, '执行确认', { type: 'info' })
    const res = await executeCases([row.id])
    ElMessage.success('执行任务已创建')
  } catch {}
}

async function handleBatchExecute() {
  if (!selectedCases.value.length) return
  try {
    await ElMessageBox.confirm(`确认执行选中的 ${selectedCases.value.length} 个用例？`, '批量执行确认', { type: 'info' })
    const ids = selectedCases.value.map(c => c.id)
    const res = await executeCases(ids)
    ElMessage.success('批量执行任务已创建')
  } catch {}
}

// Recording functions
const recordSteps = ref<Array<{ action: string; selector: string; value?: string }>>([])

function showRecordDialog() {
  recordedScript.value = ''
  recordBindCaseId.value = ''
  recording.value = false
  recordSteps.value = []
  recordDialogVisible.value = true
}

function getSelector(el: HTMLElement): string {
  if (el.id) return `#${el.id}`
  const name = (el as HTMLInputElement).name
  if (name) return `[name="${name}"]`
  const path: string[] = []
  let current: HTMLElement | null = el
  while (current && current !== document.body) {
    let selector = current.tagName.toLowerCase()
    if (current.className && typeof current.className === 'string') {
      const cls = current.className.trim().split(/\s+/).slice(0, 2).join('.')
      if (cls) selector += `.${cls}`
    }
    path.unshift(selector)
    current = current.parentElement
  }
  return path.join(' > ')
}

function onRecordClick(e: MouseEvent) {
  if (!recording.value) return
  const target = e.target as HTMLElement
  if (target.closest('.record-panel') || target.closest('.el-dialog')) return
  recordSteps.value.push({ action: 'click', selector: getSelector(target) })
}

function onRecordInput(e: Event) {
  if (!recording.value) return
  const target = e.target as HTMLInputElement | HTMLTextAreaElement
  if (target.closest('.record-panel') || target.closest('.el-dialog')) return
  recordSteps.value.push({ action: 'fill', selector: getSelector(target), value: target.value })
}

function onRecordKeydown(e: KeyboardEvent) {
  if (!recording.value) return
  if (e.key === 'Enter') {
    const target = e.target as HTMLElement
    if (target.closest('.record-panel') || target.closest('.el-dialog')) return
    recordSteps.value.push({ action: 'press', selector: getSelector(target), value: 'Enter' })
  }
}

function startRecording() {
  recording.value = true
  recordSteps.value = []
  document.addEventListener('click', onRecordClick, true)
  document.addEventListener('input', onRecordInput, true)
  document.addEventListener('keydown', onRecordKeydown, true)
  ElMessage.info('录制已开始，请在页面上操作')
}

function stopRecording() {
  recording.value = false
  document.removeEventListener('click', onRecordClick, true)
  document.removeEventListener('input', onRecordInput, true)
  document.removeEventListener('keydown', onRecordKeydown, true)
  // Generate Playwright script
  const lines = recordSteps.value.map(step => {
    if (step.action === 'click') return `  await page.locator('${step.selector}').click()`
    if (step.action === 'fill') return `  await page.locator('${step.selector}').fill('${step.value}')`
    if (step.action === 'press') return `  await page.locator('${step.selector}').press('${step.value}')`
    return ''
  })
  recordedScript.value = `import { test, expect } from '@playwright/test'\n\ntest('recorded test', async ({ page }) => {\n  await page.goto('http://localhost')\n${lines.join('\n')}\n})`
  ElMessage.success(`录制完成，共 ${recordSteps.value.length} 个步骤`)
}

async function bindRecordedScript() {
  if (!recordBindCaseId.value || !recordedScript.value) return
  try {
    await updateCase(recordBindCaseId.value, { ui_script: recordedScript.value, ui_script_type: 'PLAYWRIGHT' })
    ElMessage.success('脚本已绑定到用例')
    recordDialogVisible.value = false
    fetchData()
  } catch {
    ElMessage.error('绑定失败')
  }
}

fetchData()
fetchAuthors()
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
.filter-form { margin-bottom:16px; }
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }
.record-panel { text-align:center; padding:20px; }
.record-start p, .record-active p, .record-done p { margin-bottom:20px; color:var(--el-text-color-secondary); }
.record-indicator { display:flex; align-items:center; justify-content:center; gap:8px; margin-bottom:16px; font-size:18px; color:var(--el-color-danger); }
.record-dot { width:12px; height:12px; border-radius:50%; background:var(--el-color-danger); animation: pulse 1s infinite; }
@keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.3; } }
</style>
