<template>
  <div class="case-list">
    <!-- Top: Filters -->
    <div class="filter-bar">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="类型"><el-select v-model="filters.type" style="width:160px" clearable placeholder="全部" @change="fetchData"><el-option label="API" value="API" /><el-option label="UI" value="UI" /><el-option label="性能" value="PERFORMANCE" /></el-select></el-form-item>
        <el-form-item label="状态"><el-select v-model="filters.status" style="width:160px" clearable placeholder="全部" @change="fetchData"><el-option label="草稿" value="DRAFT" /><el-option label="激活" value="ACTIVE" /><el-option label="废弃" value="DEPRECATED" /></el-select></el-form-item>
        <el-form-item label="优先级"><el-select v-model="filters.priority" style="width:160px" clearable placeholder="全部" @change="fetchData"><el-option label="BVT" value="BVT" /><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
        <el-form-item label="编写人"><el-select v-model="filters.author" style="width:160px" clearable placeholder="全部" @change="fetchData"><el-option v-for="a in authorList" :key="a" :label="a" :value="a" /></el-select></el-form-item>
        <el-form-item label="搜索"><el-input v-model="filters.keyword" placeholder="用例名称/ID" clearable @clear="fetchData" /></el-form-item>
        <el-form-item><el-button type="primary" @click="fetchData">查询</el-button></el-form-item>
      </el-form>
    </div>

    <!-- Middle/Lower: Integrated Folder Tree + Case Table -->
    <div class="main-area">
      <!-- Trash View -->
      <template v-if="showTrash">
        <el-card class="trash-card">
          <template #header>
            <div class="card-header">
              <span>垃圾桶</span>
              <div>
                <el-button type="danger" icon="Delete" @click="handleEmptyTrash">清空垃圾桶</el-button>
                <el-button @click="showTrash = false; selectedFolderId = null; selectedCaseId = null; selectedCaseName = null; fetchData()">返回</el-button>
              </div>
            </div>
          </template>
          <el-table :data="trashList" stripe border>
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{row}"><el-tag :type="row.type==='folder'?'warning':'info'" size="small">{{ row.type === 'folder' ? '文件夹' : '用例' }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="name" label="名称" min-width="200" />
            <el-table-column prop="deleted_at" label="删除时间" width="200" />
            <el-table-column label="操作" width="100">
              <template #default="{row}">
                <el-button text type="primary" size="small" @click="handleRestoreItem(row)">恢复</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </template>

      <!-- Integrated Folder + Case View -->
      <template v-else>
        <!-- Left: Folder Tree with cases -->
        <div class="folder-panel">
          <div class="folder-header">
            <span>用例目录</span>
            <el-button text type="primary" icon="Plus" @click="handleCreateRootFolder" />
          </div>
          <div class="folder-tree-wrap">
            <el-tree
              ref="treeRef"
              :data="folderTree"
              node-key="id"
              :props="{ label: 'name', children: 'children' }"
              default-expand-all
              highlight-current
              :expand-on-click-node="false"
              draggable
              :allow-drop="allowDrop"
              @node-click="handleNodeClick"
              @node-drop="handleNodeDrop"
            >
              <template #default="{ data }">
                <div class="tree-node" :class="{ 'is-case': data.type === 'case' }">
                  <el-icon v-if="data.type === 'case'" class="case-icon"><Document /></el-icon>
                  <el-icon v-else><Folder /></el-icon>
                  <span class="node-label">{{ data.name }}</span>
                  <template v-if="data.type !== 'case'">
                    <span class="node-count">{{ data.case_count }}</span>
                    <el-dropdown trigger="click" @command="(cmd: string) => handleFolderCommand(cmd, data)" @click.stop>
                      <el-icon class="node-more"><MoreFilled /></el-icon>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="addSub">新建子文件夹</el-dropdown-item>
                          <el-dropdown-item command="rename">重命名</el-dropdown-item>
                          <el-dropdown-item command="copy">复制</el-dropdown-item>
                          <el-dropdown-item command="delete" divided>删除</el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </template>
                  <template v-else>
                    <el-icon class="action-btn" title="复制用例" @click.stop="handleCopyCaseById(data.id)"><CopyDocument /></el-icon>
                    <el-icon class="action-btn action-btn--delete" title="删除用例" @click.stop="handleDeleteCaseFromTree(data)"><Delete /></el-icon>
                  </template>
                </div>
              </template>
            </el-tree>
          </div>
          <div class="trash-node" :class="{ active: showTrash }" @click="handleTrashClick">
            <el-icon><Delete /></el-icon>
            <span>垃圾桶</span>
            <span v-if="trashCount > 0" class="trash-count">{{ trashCount }}</span>
          </div>
        </div>

        <!-- Right: Case Table -->
        <div class="case-panel">
          <div class="case-header">
            <span class="case-title">{{ selectedCaseName || selectedFolderName }}</span>
            <div>
              <el-button type="warning" icon="CaretRight" :disabled="!selectedCases.length" @click="handleBatchExecute">批量执行({{ selectedCases.length }})</el-button>
              <el-button type="success" icon="VideoCamera" @click="showRecordDialog">用例录制</el-button>
              <el-button type="primary" icon="Plus" @click="handleCreate">新建用例</el-button>
            </div>
          </div>
          <el-table :data="caseList" v-loading="loading" stripe border @selection-change="handleSelectionChange" :row-class-name="caseRowClass" @row-click="handleCaseRowClick">
            <el-table-column type="selection" width="50" />
            <el-table-column prop="id" label="用例ID" width="280" show-overflow-tooltip />
            <el-table-column prop="name" label="用例名称" min-width="200">
              <template #default="{row}">
                <div class="name-cell">
                  <span class="name-text" :title="row.name">{{ row.name }}</span>
                  <el-icon class="name-copy-btn" title="复制名称" @click.stop="copyCaseName(row.name)"><CopyDocument /></el-icon>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="type" label="类型" width="100"><template #default="{row}"><el-tag size="small">{{ row.type }}</el-tag></template></el-table-column>
            <el-table-column prop="priority" label="优先级" width="80"><template #default="{row}"><el-tag :type="row.priority==='BVT'?'danger':row.priority==='P0'?'danger':row.priority==='P1'?'warning':''" size="small">{{ row.priority }}</el-tag></template></el-table-column>
            <el-table-column prop="author" label="编写人" width="100" show-overflow-tooltip />
            <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='ACTIVE'?'success':row.status==='DEPRECATED'?'info':''" size="small">{{ row.status }}</el-tag></template></el-table-column>
            <el-table-column label="操作" width="200" fixed="right">
              <template #default="{row}">
                <el-button text type="success" size="small" @click.stop="handleExecute(row)">执行</el-button>
                <el-button text type="primary" size="small" @click.stop="handleEdit(row)">编辑</el-button>
                <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small" @click.stop>删除</el-button></template></el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
          <el-pagination class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10,20,50]" layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
        </div>
      </template>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑用例' : '新建用例'" width="780px" destroy-on-close draggable>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="基本信息" name="basic">
            <el-form-item label="用例ID" v-if="isEdit"><el-input :model-value="editingId" disabled /></el-form-item>
            <el-form-item label="所属文件夹" prop="folder_id">
              <el-tree-select v-model="form.folder_id" :data="folderOnlyTree" :props="{ label: 'name', children: 'children', value: 'id' }" placeholder="请选择文件夹" style="width:100%" check-strictly default-expand-all />
            </el-form-item>
            <el-form-item label="用例名称" prop="name"><el-input v-model="form.name" placeholder="请输入用例名称" /></el-form-item>
            <el-form-item label="用例类型" prop="type"><el-select v-model="form.type" placeholder="请选择类型" @change="onTypeChange"><el-option label="API" value="API" /><el-option label="UI" value="UI" /><el-option label="性能测试" value="PERFORMANCE" /></el-select></el-form-item>
            <el-form-item label="优先级"><el-select v-model="form.priority"><el-option label="BVT" value="BVT" /><el-option label="P0" value="P0" /><el-option label="P1" value="P1" /><el-option label="P2" value="P2" /><el-option label="P3" value="P3" /></el-select></el-form-item>
            <el-form-item label="编写人"><el-input v-model="form.author" placeholder="用例编写人" /></el-form-item>
            <el-form-item label="所属模块"><el-input v-model="form.module" placeholder="所属模块" /></el-form-item>
            <el-form-item label="标签"><el-select v-model="form.tags" multiple filterable allow-create placeholder="输入标签后回车" /></el-form-item>
            <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
          </el-tab-pane>
          <el-tab-pane label="操作步骤" name="steps">
            <el-form-item label="前置条件"><el-input v-model="form.preconditions" type="textarea" :rows="3" placeholder="执行用例前需要满足的前置条件" /></el-form-item>
            <el-form-item label="操作步骤"><el-input v-model="form.stepsText" type="textarea" :rows="6" placeholder="描述具体的操作步骤" /></el-form-item>
            <el-form-item label="预期结果"><el-input v-model="form.expected_result" type="textarea" :rows="2" placeholder="总体预期结果" /></el-form-item>
            <el-form-item label="后置条件"><el-input v-model="form.postconditions" type="textarea" :rows="3" placeholder="用例执行完成后的后置条件" /></el-form-item>
          </el-tab-pane>
          <el-tab-pane label="接口配置" name="api" v-if="form.type === 'API'">
            <el-form-item label="接口地址"><el-input v-model="form.api_url" placeholder="http://example.com/api/v1/xxx" /></el-form-item>
            <el-form-item label="请求方法"><el-select v-model="form.api_method"><el-option label="GET" value="GET" /><el-option label="POST" value="POST" /><el-option label="PUT" value="PUT" /><el-option label="DELETE" value="DELETE" /><el-option label="PATCH" value="PATCH" /></el-select></el-form-item>
            <el-form-item label="请求头"><el-input v-model="apiHeadersStr" type="textarea" :rows="3" placeholder='{"Content-Type": "application/json"}' /></el-form-item>
            <el-form-item label="请求体类型"><el-select v-model="form.api_body_type"><el-option label="JSON" value="JSON" /><el-option label="FORM" value="FORM" /><el-option label="XML" value="XML" /><el-option label="RAW" value="RAW" /><el-option label="NONE" value="NONE" /></el-select></el-form-item>
            <el-form-item label="请求体"><el-input v-model="form.api_body" type="textarea" :rows="4" placeholder="请求体内容" /></el-form-item>
            <el-form-item label="超时(ms)"><el-input-number v-model="form.api_timeout" :min="1000" :max="300000" :step="1000" /></el-form-item>
          </el-tab-pane>
          <el-tab-pane label="UI配置" name="ui" v-if="form.type === 'UI'">
            <el-form-item label="页面地址"><el-input v-model="form.ui_url" placeholder="http://example.com/page" /></el-form-item>
            <el-form-item label="脚本类型"><el-select v-model="form.ui_script_type"><el-option label="手动" value="MANUAL" /><el-option label="Playwright" value="PLAYWRIGHT" /><el-option label="Selenium" value="SELENIUM" /></el-select></el-form-item>
            <el-form-item label="自动化脚本"><el-input v-model="form.ui_script" type="textarea" :rows="6" placeholder="自动化脚本内容" /></el-form-item>
          </el-tab-pane>
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
    <el-dialog v-model="recordDialogVisible" title="用例录制" width="90vw" top="5vh" draggable @close="handleRecordClose">
      <div class="record-toolbar">
        <el-input v-model="recordTargetUrl" placeholder="输入目标地址，如 http://example.com" clearable
          :disabled="recordStatus !== 'idle'" style="flex:1" @keyup.enter="handleRecordStart" />
        <el-button v-if="recordStatus === 'idle'" type="danger" icon="VideoCamera" @click="handleRecordStart">开始录制</el-button>
        <el-button v-if="recordStatus === 'recording'" type="info" icon="VideoPause" @click="handleRecordStop">停止录制</el-button>
        <el-button v-if="recordStatus === 'stopped'" type="danger" icon="VideoCamera" @click="handleRecordStart">重新录制</el-button>
        <span v-if="recordStatus === 'recording'" class="record-indicator">
          <span class="record-dot"></span>录制中 {{ recordFrameCount }} 帧
        </span>
      </div>
      <div class="record-viewport">
        <canvas ref="recordCanvasRef" class="record-canvas"
          :style="{ cursor: recordStatus === 'recording' ? 'crosshair' : 'default' }" />
        <div v-if="recordStatus === 'idle'" class="record-placeholder">
          <el-icon :size="48"><VideoCamera /></el-icon>
          <p>输入目标地址并点击"开始录制"</p>
        </div>
      </div>
      <div class="record-footer">
        <el-select v-model="recordBindCaseId" placeholder="选择要绑定的用例" filterable style="flex:1">
          <el-option v-for="c in caseList" :key="c.id" :label="`${c.name} (${c.id.slice(0,8)}...)`" :value="c.id" />
        </el-select>
        <el-button type="primary" :disabled="!recordBindCaseId || !recordedScript.trim()" @click="bindRecordedScript">绑定到用例</el-button>
      </div>
      <el-input v-if="recordedScript" v-model="recordedScript" type="textarea" :rows="6" placeholder="录制脚本预览" readonly style="margin-top:12px" />
    </el-dialog>

    <!-- Batch Execute Dialog -->
    <el-dialog v-model="batchDialogVisible" title="批量执行" width="480px" draggable destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="任务名称" required>
          <el-input v-model="batchTaskName" placeholder="请输入任务名称" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="用例数量">
          <el-tag>{{ selectedCases.length }} 个用例</el-tag>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="batchSubmitting" @click="handleBatchSubmit">确认执行</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import {
  getCaseList, createCase, updateCase, getCaseDetail, deleteCase, getCaseAuthors, executeCases, copyCase,
  getFolderTree, createFolder, updateFolder, deleteFolder, copyFolder,
  getTrashList, emptyTrash, restoreTrashItem,
  startRecording, stopRecording,
} from '@/api/cases'

const loading = ref(false)
const caseList = ref<any[]>([])
const authorList = ref<string[]>([])
const selectedCases = ref<any[]>([])
const filters = reactive({ type: '', status: '', priority: '', author: '', keyword: '' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// Folder state
const treeRef = ref<any>(null)
const folderTree = ref<any[]>([])
const selectedFolderId = ref<string | null>(null)
const selectedFolderName = ref<string>('全部用例')
const selectedCaseId = ref<string | null>(null)
const selectedCaseName = ref<string | null>(null)
const showTrash = ref(false)
const trashList = ref<any[]>([])
const trashCount = ref(0)
const highlightedCaseId = ref<string | null>(null)

// Folder-only tree for tree-select (strips case leaf nodes)
function filterFolderOnly(nodes: any[]): any[] {
  return nodes
    .filter(n => n.type !== 'case')
    .map(n => ({ ...n, children: n.children ? filterFolderOnly(n.children) : [] }))
}
const folderOnlyTree = computed(() => filterFolderOnly(folderTree.value))

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
const recordTargetUrl = ref('')
const recordedScript = ref('')
const recordBindCaseId = ref('')
const recordStatus = ref<'idle' | 'recording' | 'stopped'>('idle')
const recordFrameCount = ref(0)
const recordCanvasRef = ref<HTMLCanvasElement | null>(null)
let recordWs: WebSocket | null = null
let recordSessionId = ''
let recordImg: HTMLImageElement | null = null
let recordEventCleanups: (() => void)[] = []

const defaultForm = () => ({
  folder_id: selectedFolderId.value || '',
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
  api_url: '', api_method: 'GET', api_headers: null as Record<string, string> | null,
  api_body_type: 'JSON', api_body: '', api_timeout: 30000, api_assertions: [] as any[],
  ui_url: '', ui_script: '', ui_script_type: 'MANUAL',
  perf_url: '', perf_vusers: 10, perf_spawn_rate: 1, perf_duration: 60, perf_assertions: [] as any[],
})

const form = reactive(defaultForm())

const apiHeadersStr = computed({
  get: () => form.api_headers ? JSON.stringify(form.api_headers, null, 2) : '',
  set: (val: string) => { try { form.api_headers = val ? JSON.parse(val) : null } catch {} }
})

const rules: FormRules = {
  folder_id: [{ required: true, message: '请选择所属文件夹', trigger: 'change' }],
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
      folder_id: data.folder_id || '', name: data.name || '', type: data.type || 'API', priority: data.priority || 'P2',
      author: data.author || '', module: data.module || '', tags: data.tags || [],
      description: (data.description || '').replace(/^'|'$/g, ''),
      preconditions: (data.preconditions || '').replace(/^'|'$/g, ''),
      stepsText: (data.steps && data.steps.length) ? data.steps.map((s: any) => s.action || s).join('\n') : '',
      postconditions: (data.postconditions || '').replace(/^'|'$/g, ''),
      expected_result: (data.expected_result || '').replace(/^'|'$/g, ''),
      api_url: data.api_url || '', api_method: data.api_method || 'GET',
      api_headers: data.api_headers || null, api_body_type: data.api_body_type || 'JSON',
      api_body: (data.api_body || '').replace(/^'|'$/g, ''), api_timeout: data.api_timeout || 30000,
      ui_url: data.ui_url || '', ui_script: (data.ui_script || '').replace(/^'|'$/g, ''), ui_script_type: data.ui_script_type || 'MANUAL',
      perf_url: data.perf_url || '', perf_vusers: data.perf_vusers || 10,
      perf_spawn_rate: data.perf_spawn_rate || 1, perf_duration: data.perf_duration || 60,
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
      name: form.name, type: form.type, priority: form.priority,
      author: form.author || undefined, module: form.module || undefined,
      folder_id: form.folder_id || undefined,
      tags: form.tags.length ? form.tags : undefined,
      description: form.description || undefined, preconditions: form.preconditions || undefined,
      steps: form.stepsText ? [{ action: form.stepsText }] : undefined,
      postconditions: form.postconditions || undefined, expected_result: form.expected_result || undefined,
    }
    if (form.type === 'API') {
      payload.api_url = form.api_url || undefined; payload.api_method = form.api_method || undefined
      payload.api_headers = form.api_headers || undefined; payload.api_body_type = form.api_body_type || undefined
      payload.api_body = form.api_body || undefined; payload.api_timeout = form.api_timeout || undefined
    } else if (form.type === 'UI') {
      payload.ui_url = form.ui_url || undefined; payload.ui_script = form.ui_script || undefined
      payload.ui_script_type = form.ui_script_type || undefined
    } else if (form.type === 'PERFORMANCE') {
      payload.perf_url = form.perf_url || undefined; payload.perf_vusers = form.perf_vusers || undefined
      payload.perf_spawn_rate = form.perf_spawn_rate || undefined; payload.perf_duration = form.perf_duration || undefined
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
    fetchFolderTree()
  } catch {} finally { submitting.value = false }
}

async function fetchData() {
  loading.value = true
  try {
    const params: any = { ...filters, page: pagination.page, pageSize: pagination.pageSize }
    if (selectedFolderId.value) params.folder_id = selectedFolderId.value
    const res = await getCaseList(params)
    caseList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

async function fetchSingleCase(caseId: string) {
  loading.value = true
  try {
    const res = await getCaseDetail(caseId)
    caseList.value = res.data ? [res.data] : []
    pagination.total = 1
    pagination.page = 1
  } catch {} finally { loading.value = false }
}

async function fetchAuthors() {
  try { const res = await getCaseAuthors(); authorList.value = res.data || [] } catch {}
}

async function handleDelete(id: string) {
  try {
    await deleteCase(id)
    ElMessage.success('删除成功')
    if (selectedCaseId.value === id) {
      selectedCaseId.value = null
      selectedCaseName.value = null
    }
    fetchData()
    fetchFolderTree()
  } catch {}
}

// Execution
function handleSelectionChange(selection: any[]) { selectedCases.value = selection }

function formatNow() {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function handleExecute(row: any) {
  try {
    const taskName = `${formatNow()}-${row.name}`
    await executeCases([row.id], taskName)
    ElMessage.success('执行任务已创建')
  } catch {}
}

// Batch execute dialog state
const batchDialogVisible = ref(false)
const batchTaskName = ref('')
const batchSubmitting = ref(false)

function handleBatchExecute() {
  if (!selectedCases.value.length) return
  batchTaskName.value = ''
  batchDialogVisible.value = true
}

async function handleBatchSubmit() {
  if (!batchTaskName.value.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  batchSubmitting.value = true
  try {
    await executeCases(selectedCases.value.map(c => c.id), batchTaskName.value.trim())
    ElMessage.success('批量执行任务已创建')
    batchDialogVisible.value = false
  } catch {} finally { batchSubmitting.value = false }
}

async function handleCopyCaseById(id: string) {
  try {
    await copyCase(id)
    ElMessage.success('用例已复制')
    fetchData()
    fetchFolderTree()
  } catch {}
}

async function handleDeleteCaseFromTree(data: any) {
  try {
    await ElMessageBox.confirm(`确认删除用例"${data.name}"？`, '删除确认', { type: 'warning' })
    await deleteCase(data.id)
    ElMessage.success('删除成功')
    if (selectedCaseId.value === data.id) {
      selectedCaseId.value = null
      selectedCaseName.value = null
    }
    fetchData()
    fetchFolderTree()
  } catch {}
}

// Drag and drop: only allow cases to be dropped onto folders
function allowDrop(draggingNode: any, dropNode: any, type: string) {
  if (draggingNode.data.type !== 'case') return false
  if (dropNode.data.type === 'case') return false
  return true
}

async function handleNodeDrop(draggingNode: any, dropNode: any) {
  const caseId = draggingNode.data.id
  const targetFolderId = dropNode.data.id
  try {
    await updateCase(caseId, { folder_id: targetFolderId })
    ElMessage.success('移动成功')
    fetchData()
    fetchFolderTree()
  } catch {
    ElMessage.error('移动失败')
  }
}

function copyCaseName(name: string) {
  const textarea = document.createElement('textarea')
  textarea.value = name
  textarea.style.position = 'fixed'
  textarea.style.left = '-9999px'
  document.body.appendChild(textarea)
  textarea.select()
  try {
    document.execCommand('copy')
    ElMessage.success('已复制用例名称')
  } catch {
    ElMessage.error('复制失败')
  }
  document.body.removeChild(textarea)
}

// Folder functions
async function fetchFolderTree() {
  try {
    const res = await getFolderTree()
    folderTree.value = res.data || []
    // Count trash items
    const trashRes = await getTrashList()
    trashCount.value = (trashRes.data || []).length
  } catch {}
}

function handleNodeClick(data: any) {
  if (data.type === 'case') {
    // Clicked a case leaf node: show only this case in the table
    highlightedCaseId.value = data.id
    selectedCaseId.value = data.id
    selectedCaseName.value = data.name
    showTrash.value = false
    fetchSingleCase(data.id)
    return
  }
  // Clicked a folder: select it and filter the table
  highlightedCaseId.value = null
  selectedCaseId.value = null
  selectedCaseName.value = null
  selectedFolderId.value = data.id
  selectedFolderName.value = data.name
  showTrash.value = false
  pagination.page = 1
  fetchData()
}

function handleCaseRowClick(row: any) {
  highlightedCaseId.value = row.id
  if (selectedCaseId.value) {
    selectedCaseId.value = row.id
    selectedCaseName.value = row.name
  }
}

function caseRowClass({ row }: { row: any }) {
  return row.id === highlightedCaseId.value ? 'highlighted-row' : ''
}

async function handleCreateRootFolder() {
  try {
    const { value } = await ElMessageBox.prompt('请输入文件夹名称', '新建文件夹', { inputPattern: /\S+/, inputErrorMessage: '名称不能为空' })
    await createFolder({ name: value })
    ElMessage.success('创建成功')
    fetchFolderTree()
  } catch {}
}

async function handleCreateSubFolder(parentId: string) {
  try {
    const { value } = await ElMessageBox.prompt('请输入子文件夹名称', '新建子文件夹', { inputPattern: /\S+/, inputErrorMessage: '名称不能为空' })
    await createFolder({ name: value, parent_id: parentId })
    ElMessage.success('创建成功')
    fetchFolderTree()
  } catch {}
}

async function handleRenameFolder(folderId: string) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新名称', '重命名', { inputPattern: /\S+/, inputErrorMessage: '名称不能为空' })
    await updateFolder(folderId, { name: value })
    ElMessage.success('重命名成功')
    fetchFolderTree()
  } catch {}
}

async function handleDeleteFolder(folderId: string) {
  try {
    await ElMessageBox.confirm('删除文件夹将同时删除其中的所有用例，确认删除？', '删除确认', { type: 'warning' })
    await deleteFolder(folderId)
    ElMessage.success('删除成功')
    if (selectedFolderId.value === folderId) {
      selectedFolderId.value = null
      selectedFolderName.value = '全部用例'
      selectedCaseId.value = null
      selectedCaseName.value = null
    }
    fetchFolderTree()
    fetchData()
  } catch {}
}

async function handleCopyFolderCmd(folderId: string) {
  try {
    await copyFolder(folderId)
    ElMessage.success('复制成功')
    fetchFolderTree()
  } catch {}
}

function handleFolderCommand(cmd: string, data: any) {
  if (cmd === 'addSub') handleCreateSubFolder(data.id)
  else if (cmd === 'rename') handleRenameFolder(data.id)
  else if (cmd === 'copy') handleCopyFolderCmd(data.id)
  else if (cmd === 'delete') handleDeleteFolder(data.id)
}

// Trash functions
async function handleTrashClick() {
  showTrash.value = true
  selectedFolderId.value = null
  selectedCaseId.value = null
  selectedCaseName.value = null
  highlightedCaseId.value = null
  try { const res = await getTrashList(); trashList.value = res.data || [] } catch {}
}

async function handleRestoreItem(row: any) {
  try {
    await restoreTrashItem(row.type, row.id)
    ElMessage.success('恢复成功')
    handleTrashClick()
    fetchFolderTree()
    fetchData()
  } catch {}
}

async function handleEmptyTrash() {
  try {
    await ElMessageBox.confirm('清空垃圾桶将永久删除所有已删除的文件夹和用例，此操作不可恢复！', '清空确认', { type: 'error', confirmButtonText: '确认清空' })
    await emptyTrash()
    ElMessage.success('垃圾桶已清空')
    trashList.value = []
    trashCount.value = 0
  } catch {}
}

function showRecordDialog() {
  recordTargetUrl.value = ''
  recordedScript.value = ''
  recordBindCaseId.value = ''
  recordStatus.value = 'idle'
  recordFrameCount.value = 0
  recordSessionId = ''
  recordDialogVisible.value = true
}

function mapRecordCoords(canvas: HTMLCanvasElement, clientX: number, clientY: number) {
  const rect = canvas.getBoundingClientRect()
  return {
    x: Math.round((clientX - rect.left) * (1280 / rect.width)),
    y: Math.round((clientY - rect.top) * (720 / rect.height)),
  }
}

function sendRecordEvent(event: any) {
  if (recordWs && recordWs.readyState === WebSocket.OPEN) {
    recordWs.send(JSON.stringify(event))
  }
}

function bindRecordCanvasEvents(canvas: HTMLCanvasElement) {
  const onClick = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    sendRecordEvent({ type: 'click', x, y })
  }
  const onDblClick = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    sendRecordEvent({ type: 'dblclick', x, y })
  }
  const onWheel = (e: WheelEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    sendRecordEvent({ type: 'scroll', deltaX: e.deltaX, deltaY: e.deltaY })
  }
  const onKeyDown = (e: KeyboardEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    e.stopPropagation()
    if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
      sendRecordEvent({ type: 'type', text: e.key })
    } else {
      sendRecordEvent({ type: 'keypress', key: e.key })
    }
  }
  canvas.addEventListener('click', onClick)
  canvas.addEventListener('dblclick', onDblClick)
  canvas.addEventListener('wheel', onWheel, { passive: false })
  document.addEventListener('keydown', onKeyDown, true)
  recordEventCleanups.push(() => {
    canvas.removeEventListener('click', onClick)
    canvas.removeEventListener('dblclick', onDblClick)
    canvas.removeEventListener('wheel', onWheel)
    document.removeEventListener('keydown', onKeyDown, true)
  })
}

async function handleRecordStart() {
  if (!recordTargetUrl.value.trim()) {
    ElMessage.warning('请输入目标地址')
    return
  }
  recordStatus.value = 'recording'
  recordFrameCount.value = 0
  try {
    const res = await startRecording(recordTargetUrl.value.trim())
    recordSessionId = res.data.session_id
    const wsProtocol = location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${wsProtocol}//${location.host}${res.data.ws_url}`
    await new Promise<void>((resolve, reject) => {
      recordWs = new WebSocket(wsUrl)
      recordWs.binaryType = 'arraybuffer'
      recordWs.onopen = () => resolve()
      recordWs.onerror = () => reject(new Error('连接失败'))
      recordWs.onmessage = (event: MessageEvent) => {
        const canvas = recordCanvasRef.value
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return
        const blob = new Blob([event.data], { type: 'image/jpeg' })
        const url = URL.createObjectURL(blob)
        if (!recordImg) recordImg = new Image()
        recordImg.onload = () => {
          canvas.width = recordImg!.width
          canvas.height = recordImg!.height
          ctx!.drawImage(recordImg!, 0, 0)
          URL.revokeObjectURL(url)
          recordFrameCount.value++
        }
        recordImg.src = url
      }
      recordWs.onclose = () => {
        if (recordStatus.value === 'recording') recordStatus.value = 'stopped'
      }
    })
    await nextTick()
    if (recordCanvasRef.value) {
      bindRecordCanvasEvents(recordCanvasRef.value)
    }
    ElMessage.success('录制已开始，请在下方浏览器画面中操作')
  } catch (e: any) {
    ElMessage.error('启动录制失败: ' + (e.message || ''))
    recordStatus.value = 'idle'
  }
}

async function handleRecordStop() {
  if (!recordSessionId) return
  try {
    if (recordWs) { recordWs.send(JSON.stringify({ type: 'stop' })); recordWs.close(); recordWs = null }
    recordEventCleanups.forEach(fn => fn())
    recordEventCleanups = []
    const res = await stopRecording(recordSessionId)
    recordedScript.value = res.data.script || ''
    recordStatus.value = 'stopped'
    recordSessionId = ''
    ElMessage.success('录制完成')
  } catch { ElMessage.error('停止录制失败') }
}

function handleRecordClose() {
  if (recordStatus.value === 'recording' && recordSessionId) {
    if (recordWs) { recordWs.send(JSON.stringify({ type: 'stop' })); recordWs.close(); recordWs = null }
    recordEventCleanups.forEach(fn => fn())
    recordEventCleanups = []
    stopRecording(recordSessionId).catch(() => {})
  }
  if (recordWs) { recordWs.close(); recordWs = null }
  recordEventCleanups.forEach(fn => fn())
  recordEventCleanups = []
  recordImg = null
  recordStatus.value = 'idle'
  recordSessionId = ''
}

async function bindRecordedScript() {
  if (!recordBindCaseId.value || !recordedScript.value) return
  try {
    await updateCase(recordBindCaseId.value, { ui_script: recordedScript.value, ui_script_type: 'PLAYWRIGHT' })
    ElMessage.success('脚本已绑定到用例')
    recordDialogVisible.value = false
    fetchData()
  } catch { ElMessage.error('绑定失败') }
}

fetchData()
fetchAuthors()
fetchFolderTree()
</script>

<style scoped>
.case-list { display: flex; flex-direction: column; gap: 12px; height: calc(100vh - 120px); }
.filter-bar { background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 8px; padding: 12px 16px 0; }
.filter-form { margin-bottom: 0; }
.main-area { display: flex; gap: 12px; flex: 1; min-height: 0; }
.folder-panel { width: 280px; flex-shrink: 0; background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.folder-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; font-weight: 600; border-bottom: 1px solid var(--el-border-color-lighter); }
.folder-tree-wrap { flex: 1; overflow-y: auto; padding: 8px; }
.case-panel { flex: 1; min-width: 0; background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.case-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; font-weight: 600; border-bottom: 1px solid var(--el-border-color-lighter); flex-shrink: 0; }
.case-title { font-size: 15px; }
.case-panel .el-table { flex: 1; }
.case-panel :deep(.el-table__body-wrapper) { overflow-y: auto; }
.tree-node { display: flex; align-items: center; gap: 6px; flex: 1; min-width: 0; }
.tree-node.is-case { padding-left: 4px; }
.case-icon { color: var(--el-color-primary); font-size: 14px; }
.node-label { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; }
.node-count { font-size: 11px; color: var(--el-text-color-secondary); background: var(--el-fill-color-light); padding: 0 6px; border-radius: 10px; }
.action-btn { opacity: 0; color: var(--el-text-color-secondary); cursor: pointer; font-size: 13px; margin-left: 4px; }
.action-btn:hover { color: var(--el-color-primary); }
.action-btn--delete:hover { color: var(--el-color-danger); }
.tree-node:hover .action-btn { opacity: 1; }
.name-cell { display: flex; align-items: center; gap: 6px; }
.name-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.name-copy-btn { opacity: 0; color: var(--el-text-color-secondary); cursor: pointer; font-size: 14px; flex-shrink: 0; }
.name-copy-btn:hover { color: var(--el-color-primary); }
.name-cell:hover .name-copy-btn { opacity: 1; }
.node-more { opacity: 0; margin-left: auto; }
.tree-node:hover .node-more { opacity: 1; }
.trash-node { display: flex; align-items: center; gap: 8px; padding: 10px 16px; cursor: pointer; border-top: 1px solid var(--el-border-color-lighter); color: var(--el-text-color-secondary); font-size: 13px; }
.trash-node:hover, .trash-node.active { background: var(--el-fill-color-light); color: var(--el-text-color-primary); }
.trash-count { font-size: 11px; background: var(--el-color-danger); color: #fff; padding: 0 6px; border-radius: 10px; }
.trash-card { flex: 1; min-width: 0; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.pagination { margin-top: 12px; display: flex; justify-content: flex-end; padding: 0 16px 12px; }
:deep(.highlighted-row) { background-color: var(--el-color-primary-light-9) !important; }
:deep(.highlighted-row:hover > td) { background-color: var(--el-color-primary-light-8) !important; }
.record-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.record-viewport { width: 100%; height: 60vh; background: #1a1a2e; border-radius: 8px; overflow: hidden; position: relative; display: flex; align-items: center; justify-content: center; }
.record-canvas { max-width: 100%; max-height: 100%; object-fit: contain; }
.record-placeholder { position: absolute; display: flex; flex-direction: column; align-items: center; gap: 12px; color: var(--el-text-color-secondary); }
.record-footer { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.record-indicator { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--el-color-danger); font-weight: 600; }
.record-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--el-color-danger); animation: pulse 1s infinite; }
.frame-counter { font-size: 12px; color: var(--el-text-color-secondary); font-weight: 400; }
@keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.3; } }
</style>
