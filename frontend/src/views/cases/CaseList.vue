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
              <el-button type="info" icon="VideoPlay" :disabled="!selectedCases.length || !hasRecordedScript" @click="showReplayDialog">用例回放</el-button>
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
            <el-table-column prop="type" label="类型" width="100"><template #default="{row}"><el-tag size="small">{{ typeLabelMap[row.type] || row.type }}</el-tag></template></el-table-column>
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
            <el-form-item label="性能脚本"><el-input v-model="form.perf_script" type="textarea" :rows="12" placeholder="Locust 性能测试脚本" /></el-form-item>
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
        <!-- Assert context menu -->
        <div v-if="assertContextMenu.visible" class="assert-context-menu"
          :style="{ left: assertContextMenu.x + 'px', top: assertContextMenu.y + 'px' }"
          @click.stop>
          <div class="assert-menu-title">添加断言</div>
          <div class="assert-menu-item" @click="handleAssertSelect('text')">断言文本内容</div>
          <div class="assert-menu-item" @click="handleAssertSelect('visible')">断言元素可见</div>
          <div class="assert-menu-item" @click="handleAssertSelect('value')">断言输入框值</div>
          <div class="assert-menu-item" @click="handleAssertSelect('url')">断言URL</div>
          <div class="assert-menu-item" @click="handleAssertSelect('color')">断言颜色</div>
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

    <!-- Assert Dialog -->
    <el-dialog v-model="assertDialogVisible" title="配置断言" width="420px" draggable destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="断言类型">
          <el-tag>{{ assertTypeLabel }}</el-tag>
        </el-form-item>
        <el-form-item label="期望值" required>
          <el-input v-model="assertForm.expectedValue" :placeholder="assertPlaceholder" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assertDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAssert">确认</el-button>
      </template>
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

    <!-- Replay Dialog -->
    <el-dialog v-model="replayDialogVisible" title="用例回放" width="90vw" top="5vh" draggable @close="handleReplayClose">
      <div class="replay-header">
        <el-select v-model="replayCaseId" placeholder="选择要回放的用例" filterable @change="loadReplayScript" style="flex:1">
          <el-option v-for="c in recordedCases" :key="c.id" :label="`${c.name} (${c.id.slice(0,8)}...)`" :value="c.id" />
        </el-select>
        <el-button
          :type="replayStatus === 'idle' || replayStatus === 'finished' ? 'primary' : replayStatus === 'playing' ? 'success' : 'danger'"
          :icon="replayStatus === 'idle' || replayStatus === 'finished' ? 'VideoPlay' : replayStatus === 'playing' ? 'VideoPause' : 'VideoPlay'"
          :disabled="!replayScript"
          @click="handleReplayAction"
        >
          {{ replayStatus === 'idle' || replayStatus === 'finished' ? '开始回放' : replayStatus === 'playing' ? '回放中' : '已暂停' }}
        </el-button>
        <el-button type="danger" icon="Close" :disabled="replayStatus === 'idle' || replayStatus === 'finished'" @click="stopReplay">结束回放</el-button>
      </div>
      <div class="replay-viewport">
        <div v-if="!replayScript" class="replay-placeholder">
          <el-icon :size="48"><VideoPlay /></el-icon>
          <p>选择用例并点击"开始回放"查看录制结果</p>
        </div>
        <div v-if="replayScript && replayStatus !== 'idle'" class="replay-content">
          <div class="replay-steps">
            <div class="replay-steps-header">回放步骤</div>
            <div class="replay-steps-list">
              <div
                v-for="(step, index) in replaySteps"
                :key="index"
                class="replay-step-item clickable"
                :class="{
                  'active': index === replayStep - 1,
                  'completed': index < replayStep - 1,
                  'selected': index === selectedStep
                }"
                @click="handleStepClick(index)"
              >
                <div class="step-number">{{ index + 1 }}</div>
                <div class="step-content">{{ step }}</div>
              </div>
            </div>
          </div>
          <div class="replay-preview">
            <div class="replay-preview-header">回放预览</div>
            <div class="replay-preview-content">
              <canvas ref="replayCanvasRef" class="replay-canvas" />
              <div v-if="replayStatus === 'playing'" class="replay-indicator">
                <span class="replay-dot"></span>回放中 {{ replayStep }}/{{ replayTotalSteps }}
              </div>
              <div v-if="replayStatus === 'paused'" class="replay-indicator paused">
                <span class="replay-dot paused"></span>已暂停 {{ replayStep }}/{{ replayTotalSteps }}
              </div>
              <div v-if="replayStatus === 'finished' && selectedStep === null" class="replay-finished">
                <el-icon :size="48" color="#67c23a"><CircleCheckFilled /></el-icon>
                <p>回放完成</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-if="replayScript" class="replay-footer">
        <el-input v-model="replayScript" type="textarea" :rows="6" placeholder="录制脚本内容" readonly />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, nextTick, watch } from 'vue'
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
const recordedUrl = ref('')
const recordBindCaseId = ref('')
const recordStatus = ref<'idle' | 'recording' | 'stopped'>('idle')
const recordFrameCount = ref(0)
const recordCanvasRef = ref<HTMLCanvasElement | null>(null)
let recordWs: WebSocket | null = null
let recordSessionId = ''
let recordImg: HTMLImageElement | null = null
let recordEventCleanups: (() => void)[] = []

// Replay dialog state
const replayDialogVisible = ref(false)
const replayCaseId = ref('')
const replayScript = ref('')
const replayStatus = ref<'idle' | 'playing' | 'paused' | 'finished'>('idle')
const replayStep = ref(0)
const replayTotalSteps = ref(0)
const replayCanvasRef = ref<HTMLCanvasElement | null>(null)
const replaySteps = ref<string[]>([])
const selectedStep = ref<number | null>(null)
let replayAbortController: AbortController | null = null
// Screenshots captured during recording for replay display
let recordedScreenshots: string[] = []
let recordedLineToAction: (number | null)[] = []

// Assertion recording state
const assertContextMenu = ref({ visible: false, x: 0, y: 0, canvasX: 0, canvasY: 0 })
const assertDialogVisible = ref(false)
const assertForm = reactive({ type: '', expectedValue: '' })

const typeLabelMap: Record<string, string> = { API: 'API', UI: 'UI', PERFORMANCE: '性能' }

const DEFAULT_LOCUST_SCRIPT = `from locust import HttpUser, task, between

class MyUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def test_case(self):
        # TODO: 在此处补充业务逻辑
        # 示例: self.client.get("/api/v1/xxx")
        # 示例: self.client.post("/api/v1/xxx", json={"key": "value"})
        pass
`

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
  perf_url: '', perf_vusers: 10, perf_spawn_rate: 1, perf_duration: 60, perf_assertions: [] as any[], perf_script: DEFAULT_LOCUST_SCRIPT,
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

watch(() => form.type, (newType) => {
  if (newType === 'PERFORMANCE') {
    nextTick(() => {
      if (!form.perf_script || !form.perf_script.trim()) {
        form.perf_script = DEFAULT_LOCUST_SCRIPT
      }
    })
  }
})

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
      perf_script: data.perf_script || '',
    })
    if (form.type === 'PERFORMANCE' && (!form.perf_script || !form.perf_script.trim())) {
      form.perf_script = DEFAULT_LOCUST_SCRIPT
    }
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
      payload.perf_script = form.perf_script || undefined
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
  recordedUrl.value = ''
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
  let isDragging = false

  const onClick = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    sendRecordEvent({ type: 'click', x, y })
  }
  const onDblClick = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    sendRecordEvent({ type: 'dblclick', x, y })
  }
  const onMouseDown = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    e.stopPropagation()
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    isDragging = true
    sendRecordEvent({ type: 'mousedown', x, y })
  }
  const onMouseMove = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording' || !isDragging) return
    e.preventDefault()
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    sendRecordEvent({ type: 'mousemove', x, y })
  }
  const onMouseUp = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    if (isDragging) {
      const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
      isDragging = false
      sendRecordEvent({ type: 'mouseup', x, y })
    }
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
  canvas.addEventListener('mousedown', onMouseDown)
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  canvas.addEventListener('wheel', onWheel, { passive: false })
  document.addEventListener('keydown', onKeyDown, true)

  const onContextMenu = (e: MouseEvent) => {
    if (recordStatus.value !== 'recording') return
    e.preventDefault()
    const { x, y } = mapRecordCoords(canvas, e.clientX, e.clientY)
    const rect = canvas.getBoundingClientRect()
    assertContextMenu.value = {
      visible: true,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      canvasX: x,
      canvasY: y,
    }
  }
  canvas.addEventListener('contextmenu', onContextMenu)

  recordEventCleanups.push(() => {
    canvas.removeEventListener('click', onClick)
    canvas.removeEventListener('dblclick', onDblClick)
    canvas.removeEventListener('mousedown', onMouseDown)
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    canvas.removeEventListener('wheel', onWheel)
    document.removeEventListener('keydown', onKeyDown, true)
    canvas.removeEventListener('contextmenu', onContextMenu)
  })
}

// Close assert context menu when clicking outside
function closeAssertMenu() {
  assertContextMenu.value.visible = false
}
document.addEventListener('click', closeAssertMenu)

const assertTypeLabel = computed(() => {
  const map: Record<string, string> = { text: '文本内容', visible: '元素可见', value: '输入框值', url: 'URL', color: '颜色' }
  return map[assertForm.type] || ''
})

const assertPlaceholder = computed(() => {
  const map: Record<string, string> = {
    text: '请输入期望的文本内容',
    value: '请输入期望的输入框值',
    url: '请输入期望的URL地址',
    color: '请输入期望的颜色值，如 rgb(255, 0, 0)',
  }
  return map[assertForm.type] || ''
})

function handleAssertSelect(type: string) {
  assertContextMenu.value.visible = false
  if (type === 'visible') {
    sendAssertion('visible')
    return
  }
  assertForm.type = type
  assertForm.expectedValue = ''
  assertDialogVisible.value = true
}

function confirmAssert() {
  if (!assertForm.expectedValue.trim()) {
    ElMessage.warning('请输入期望值')
    return
  }
  assertDialogVisible.value = false
  sendAssertion(assertForm.type, assertForm.expectedValue.trim())
}

function sendAssertion(assertType: string, expectedValue?: string) {
  const payload: any = { type: 'assert', assertType }
  if (expectedValue) payload.expectedValue = expectedValue
  if (assertType !== 'url') {
    payload.x = assertContextMenu.value.canvasX
    payload.y = assertContextMenu.value.canvasY
  }
  sendRecordEvent(payload)
  ElMessage.success(`已添加${assertTypeLabel.value || assertType}断言`)
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
    recordedUrl.value = res.data.url || ''
    recordedScreenshots = res.data.screenshots || []
    recordedLineToAction = res.data.line_to_action || []
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
    const updateData: any = { ui_script: recordedScript.value, ui_script_type: 'PLAYWRIGHT' }
    if (recordedUrl.value) {
      updateData.ui_url = recordedUrl.value
    }
    if (recordedScreenshots.length > 0) {
      updateData.ui_screenshots = { screenshots: recordedScreenshots, line_to_action: recordedLineToAction }
    }
    try {
      await updateCase(recordBindCaseId.value, updateData)
    } catch {
      // If saving with screenshots fails (e.g. column not migrated), retry without
      delete updateData.ui_screenshots
      await updateCase(recordBindCaseId.value, updateData)
    }
    ElMessage.success('脚本已绑定到用例')
    recordDialogVisible.value = false
    fetchData()
  } catch { ElMessage.error('绑定失败') }
}

// Replay functions
const recordedCases = computed(() => {
  return caseList.value.filter(c => c.ui_script && c.ui_script.trim())
})

const hasRecordedScript = computed(() => {
  return selectedCases.value.some(c => c.ui_script && c.ui_script.trim())
})

function showReplayDialog() {
  replayDialogVisible.value = true
  replayCaseId.value = ''
  replayScript.value = ''
  replayStatus.value = 'idle'
  replayStep.value = 0
  selectedStep.value = null
  replayTotalSteps.value = 0
  replayScreenshotImages = []
  // Keep recordedScreenshots/recordedLineToAction if they exist from a fresh recording
  // Only clear them if there's nothing fresh
  if (recordedScreenshots.length === 0) {
    recordedLineToAction = []
  }
  // Auto select first case with script if available
  if (selectedCases.value.length === 1 && selectedCases.value[0].ui_script) {
    replayCaseId.value = selectedCases.value[0].id
    replayScript.value = selectedCases.value[0].ui_script
    parseReplaySteps()
    // Load screenshots from case data only if we don't have fresh ones from recording
    if (recordedScreenshots.length === 0) {
      const caseItem = selectedCases.value[0]
      if (caseItem.ui_screenshots) {
        recordedScreenshots = caseItem.ui_screenshots.screenshots || []
        recordedLineToAction = caseItem.ui_screenshots.line_to_action || []
      }
    }
  }
}

function loadReplayScript(caseId: string) {
  const caseItem = caseList.value.find(c => c.id === caseId)
  if (caseItem && caseItem.ui_script) {
    replayScript.value = caseItem.ui_script
    parseReplaySteps()
    // Load screenshots if available
    if (caseItem.ui_screenshots) {
      recordedScreenshots = caseItem.ui_screenshots.screenshots || []
      recordedLineToAction = caseItem.ui_screenshots.line_to_action || []
    } else {
      recordedScreenshots = []
      recordedLineToAction = []
    }
  } else {
    replayScript.value = ''
    replayTotalSteps.value = 0
    recordedScreenshots = []
    recordedLineToAction = []
  }
  replayStatus.value = 'idle'
  replayStep.value = 0
  selectedStep.value = null
}

function parseReplaySteps() {
  try {
    const allLines = replayScript.value.split('\n')
    const filteredSteps: string[] = []
    const filteredLineToAction: (number | null)[] = []
    for (let i = 0; i < allLines.length; i++) {
      const line = allLines[i]
      if (!line.trim() || line.trim().startsWith('//')) continue
      filteredSteps.push(line)
      // Map from original line index to action index
      filteredLineToAction.push(
        recordedLineToAction.length > i ? recordedLineToAction[i] : null
      )
    }
    replaySteps.value = filteredSteps
    replayTotalSteps.value = filteredSteps.length
    // Update the mapping to match filtered step indices
    recordedLineToAction = filteredLineToAction
  } catch {
    replaySteps.value = []
    replayTotalSteps.value = 0
  }
}

function handleReplayAction() {
  if (replayStatus.value === 'idle' || replayStatus.value === 'finished') {
    startReplay()
  } else if (replayStatus.value === 'playing') {
    pauseReplay()
  } else if (replayStatus.value === 'paused') {
    resumeReplay()
  }
}

async function startReplay() {
  if (!replayScript.value) return

  // Reset URL state
  currentReplayUrl = 'about:blank'

  // First set status to playing to show the canvas
  replayStatus.value = 'playing'
  replayStep.value = 0
  selectedStep.value = null
  replayAbortController = new AbortController()

  // Wait for Vue to update the DOM and show the canvas
  await nextTick()
  await new Promise(resolve => setTimeout(resolve, 300))

  // Preload screenshots if available
  await preloadReplayScreenshots()

  const canvas = replayCanvasRef.value
  if (!canvas) {
    console.error('Canvas ref is null')
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    console.error('Cannot get canvas context')
    return
  }

  // Set fixed canvas dimensions
  canvas.width = 760
  canvas.height = 460

  // Draw initial frame immediately
  drawBrowserFrame(ctx, canvas.width, canvas.height, '准备开始回放...', 0, replaySteps.value.length)

  for (let i = 0; i < replaySteps.value.length; i++) {
    if (replayAbortController?.signal.aborted) return

    // Wait while paused
    while ((replayStatus.value as string) === 'paused') {
      if (replayAbortController?.signal.aborted) return
      await new Promise(resolve => setTimeout(resolve, 100))
    }

    if (replayAbortController?.signal.aborted) return

    replayStep.value = i + 1
    const step = replaySteps.value[i].trim()

    // Draw browser-like interface
    drawBrowserFrame(ctx, canvas.width, canvas.height, step, i, replaySteps.value.length)

    // Wait between steps
    await new Promise(resolve => setTimeout(resolve, 800))
  }

  if (!replayAbortController?.signal.aborted) {
    replayStatus.value = 'finished'
    ElMessage.success('回放完成')
  }
}

async function handleStepClick(index: number) {
  selectedStep.value = index
  replayStep.value = index + 1

  const canvas = replayCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  canvas.width = 760
  canvas.height = 460

  if (replayScreenshotImages.length === 0 && recordedScreenshots.length > 0) {
    await preloadReplayScreenshots()
  }

  const step = replaySteps.value[index].trim()
  drawBrowserFrame(ctx, canvas.width, canvas.height, step, index, replaySteps.value.length)
}

// Parse Playwright script line to extract action info
function parsePlaywrightStep(step: string): { type: string; selector?: string; text?: string; url?: string; x?: number; y?: number; key?: string; deltaX?: number; deltaY?: number } {
  const trimmed = step.trim()

  // page.goto("url")
  const gotoMatch = trimmed.match(/page\.goto\(["']([^"']+)["']\)/)
  if (gotoMatch) return { type: 'goto', url: gotoMatch[1] }

  // page.click("selector") or page.dblclick("selector")
  const clickMatch = trimmed.match(/page\.(click|dblclick)\(["']([^"']+)["']\)/)
  if (clickMatch) return { type: clickMatch[1], selector: clickMatch[2] }

  // page.mouse.click(x, y) or page.mouse.dblclick(x, y)
  const mouseClickMatch = trimmed.match(/page\.mouse\.(click|dblclick)\((\d+),\s*(\d+)\)/)
  if (mouseClickMatch) return { type: mouseClickMatch[1], x: parseInt(mouseClickMatch[2]), y: parseInt(mouseClickMatch[3]) }

  // page.mouse.move(x, y)
  const mouseMoveMatch = trimmed.match(/page\.mouse\.move\((\d+),\s*(\d+)\)/)
  if (mouseMoveMatch) return { type: 'mousemove', x: parseInt(mouseMoveMatch[1]), y: parseInt(mouseMoveMatch[2]) }

  // page.mouse.down()
  if (trimmed.includes('page.mouse.down()')) return { type: 'mousedown' }

  // page.mouse.up()
  if (trimmed.includes('page.mouse.up()')) return { type: 'mouseup' }

  // page.keyboard.type("text")
  const typeMatch = trimmed.match(/page\.keyboard\.type\(["']([^"']+)["']\)/)
  if (typeMatch) return { type: 'type', text: typeMatch[1] }

  // page.keyboard.press("key")
  const keyMatch = trimmed.match(/page\.keyboard\.press\(["']([^"']+)["']\)/)
  if (keyMatch) return { type: 'keypress', key: keyMatch[1] }

  // page.mouse.wheel(deltaX, deltaY)
  const wheelMatch = trimmed.match(/page\.mouse\.wheel\(([-\d]+),\s*([-\d]+)\)/)
  if (wheelMatch) return { type: 'scroll', deltaX: parseInt(wheelMatch[1]), deltaY: parseInt(wheelMatch[2]) }

  // page.fill("selector", "text")
  const fillMatch = trimmed.match(/page\.fill\(["']([^"']+)["'],\s*["']([^"']+)["']\)/)
  if (fillMatch) return { type: 'type', selector: fillMatch[1], text: fillMatch[2] }

  // page.set_input_files or other commands
  return { type: 'other' }
}

// Extract readable name from selector
function selectorToName(selector: string): string {
  if (!selector) return '元素'
  // Extract text from selector like "text=Submit" or "button:has-text('Submit')"
  const textMatch = selector.match(/text=(.+)/) || selector.match(/:has-text\(['"](.+?)['"]\)/)
  if (textMatch) return textMatch[1]
  // Extract id from "#id"
  const idMatch = selector.match(/^#(.+)/)
  if (idMatch) return `#${idMatch[1]}`
  // Extract class from ".class"
  const classMatch = selector.match(/^\.(.+)/)
  if (classMatch) return `.${classMatch[1]}`
  // Extract tag from "tag"
  const tagMatch = selector.match(/^[a-z]+/)
  if (tagMatch) return tagMatch[0]
  return selector.length > 15 ? selector.substring(0, 15) + '...' : selector
}

// Store current page URL for address bar
let currentReplayUrl = 'about:blank'

// Preloaded screenshot images for replay (indexed by action index)
let replayScreenshotImages: (HTMLImageElement | null)[] = []

function preloadReplayScreenshots(): Promise<void> {
  return new Promise((resolve) => {
    replayScreenshotImages = []
    if (recordedScreenshots.length === 0) { resolve(); return }
    let loaded = 0
    const total = recordedScreenshots.length
    for (let i = 0; i < total; i++) {
      const b64 = recordedScreenshots[i]
      if (!b64) {
        replayScreenshotImages.push(null)
        loaded++
        if (loaded >= total) resolve()
        continue
      }
      const img = new Image()
      img.onload = () => {
        replayScreenshotImages[i] = img
        loaded++
        if (loaded >= total) resolve()
      }
      img.onerror = () => {
        replayScreenshotImages[i] = null
        loaded++
        if (loaded >= total) resolve()
      }
      img.src = 'data:image/jpeg;base64,' + b64
    }
  })
}

function drawBrowserFrame(ctx: CanvasRenderingContext2D, width: number, height: number, step: string, currentStep: number, totalSteps: number) {
  // Clear canvas
  ctx.clearRect(0, 0, width, height)

  // Parse the step
  const action = parsePlaywrightStep(step)

  // Update URL if navigating
  if (action.type === 'goto' && action.url) {
    currentReplayUrl = action.url
  }

  // Draw browser window background
  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)

  // Draw title bar
  ctx.fillStyle = '#e8e8e8'
  ctx.fillRect(0, 0, width, 40)

  // Draw window controls (red, yellow, green dots)
  ctx.fillStyle = '#ff5f57'
  ctx.beginPath()
  ctx.arc(20, 20, 6, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = '#ffbd2e'
  ctx.beginPath()
  ctx.arc(45, 20, 6, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = '#28c940'
  ctx.beginPath()
  ctx.arc(70, 20, 6, 0, Math.PI * 2)
  ctx.fill()

  // Draw address bar
  ctx.fillStyle = '#f5f5f5'
  ctx.strokeStyle = '#d0d0d0'
  ctx.lineWidth = 1
  ctx.fillRect(100, 8, width - 120, 24)
  ctx.strokeRect(100, 8, width - 120, 24)

  // Draw address bar text
  ctx.fillStyle = '#333'
  ctx.font = '12px Arial'
  const displayUrl = currentReplayUrl.length > 50 ? currentReplayUrl.substring(0, 50) + '...' : currentReplayUrl
  ctx.fillText(displayUrl, 110, 24)

  // Draw content area
  ctx.fillStyle = '#f9f9f9'
  ctx.fillRect(0, 40, width, height - 80)

  // Try to draw actual screenshot from recording
  const actionIdx = recordedLineToAction.length > currentStep ? recordedLineToAction[currentStep] : null
  const screenshotImg = actionIdx != null && actionIdx < replayScreenshotImages.length ? replayScreenshotImages[actionIdx] : null
  if (screenshotImg) {
    // Draw the actual recorded screenshot scaled to fit the content area
    const contentY = 40
    const contentH = height - 80
    const contentW = width
    const imgAspect = screenshotImg.width / screenshotImg.height
    const areaAspect = contentW / contentH
    let drawW: number, drawH: number, drawX: number, drawY: number
    if (imgAspect > areaAspect) {
      drawW = contentW
      drawH = contentW / imgAspect
      drawX = 0
      drawY = contentY + (contentH - drawH) / 2
    } else {
      drawH = contentH
      drawW = contentH * imgAspect
      drawX = (contentW - drawW) / 2
      drawY = contentY
    }
    ctx.drawImage(screenshotImg, drawX, drawY, drawW, drawH)
  } else {
    // Fall back to generic page content drawing
    drawPageContent(ctx, width, height, action, step)
  }

  // Draw action highlight
  drawActionHighlight(ctx, width, height, action)

  // Draw step info overlay
  drawStepInfo(ctx, width, height, step, currentStep, totalSteps)
}

function drawPageContent(ctx: CanvasRenderingContext2D, width: number, height: number, action: { type: string; selector?: string; text?: string; url?: string; x?: number; y?: number; key?: string; deltaX?: number; deltaY?: number }, step: string) {
  const contentY = 50
  const contentHeight = height - 90

  // Draw page header with gradient
  const gradient = ctx.createLinearGradient(0, contentY, 0, contentY + 50)
  gradient.addColorStop(0, '#409eff')
  gradient.addColorStop(1, '#337ecc')
  ctx.fillStyle = gradient
  ctx.fillRect(0, contentY, width, 50)
  ctx.fillStyle = '#fff'
  ctx.font = 'bold 16px Arial'
  ctx.fillText('Web Application', 20, contentY + 32)

  // Draw navigation bar
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, contentY + 50, width, 40)
  ctx.strokeStyle = '#e0e0e0'
  ctx.lineWidth = 1
  ctx.strokeRect(0, contentY + 50, width, 40)

  const navItems = ['首页', '产品', '关于', '联系']
  ctx.fillStyle = '#333'
  ctx.font = '14px Arial'
  navItems.forEach((item, index) => {
    ctx.fillText(item, 20 + index * 80, contentY + 75)
  })

  // Draw main content area
  ctx.fillStyle = '#fff'
  ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)
  ctx.strokeStyle = '#e0e0e0'
  ctx.strokeRect(20, contentY + 100, width - 40, contentHeight - 150)

  // Draw content based on action type
  switch (action.type) {
    case 'goto':
      // Show page loading animation
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)
      ctx.fillStyle = '#409eff'
      ctx.font = '16px Arial'
      ctx.textAlign = 'center'
      ctx.fillText('页面加载中...', width / 2, contentY + 200)
      ctx.textAlign = 'left'

      // Draw loading spinner
      ctx.strokeStyle = '#409eff'
      ctx.lineWidth = 3
      ctx.beginPath()
      ctx.arc(width / 2, contentY + 250, 20, 0, Math.PI * 1.5)
      ctx.stroke()
      ctx.lineWidth = 1

      // Show URL
      ctx.fillStyle = '#666'
      ctx.font = '12px Arial'
      ctx.textAlign = 'center'
      const urlText = action.url || ''
      ctx.fillText(urlText.length > 40 ? urlText.substring(0, 40) + '...' : urlText, width / 2, contentY + 290)
      ctx.textAlign = 'left'
      break

    case 'click':
    case 'dblclick': {
      // Draw clickable elements
      const buttonY = contentY + 180
      const buttonWidth = 120
      const buttonHeight = 36

      // Draw multiple buttons to simulate a real page
      const buttons = ['提交', '取消', '搜索', '登录']
      buttons.forEach((btnText, idx) => {
        const btnX = 40 + idx * 140
        ctx.fillStyle = idx === 0 ? '#409eff' : '#f0f0f0'
        ctx.fillRect(btnX, buttonY, buttonWidth, buttonHeight)
        ctx.fillStyle = idx === 0 ? '#fff' : '#333'
        ctx.font = '13px Arial'
        ctx.textAlign = 'center'
        ctx.fillText(btnText, btnX + buttonWidth / 2, buttonY + 23)
        ctx.textAlign = 'left'
      })

      // Draw input fields
      const inputY = contentY + 130
      ctx.fillStyle = '#fff'
      ctx.strokeStyle = '#d0d0d0'
      ctx.fillRect(40, inputY, 200, 30)
      ctx.strokeRect(40, inputY, 200, 30)
      ctx.fillRect(260, inputY, 200, 30)
      ctx.strokeRect(260, inputY, 200, 30)

      // Draw labels
      ctx.fillStyle = '#666'
      ctx.font = '12px Arial'
      ctx.fillText('用户名:', 40, inputY - 5)
      ctx.fillText('密码:', 260, inputY - 5)

      // Draw click highlight
      const targetName = selectorToName(action.selector || '')
      ctx.strokeStyle = '#ff4d4f'
      ctx.lineWidth = 3
      ctx.setLineDash([5, 5])

      // Highlight based on selector
      if (targetName.includes('提交') || targetName.includes('submit')) {
        ctx.strokeRect(40 - 2, buttonY - 2, buttonWidth + 4, buttonHeight + 4)
      } else if (targetName.includes('登录') || targetName.includes('login')) {
        ctx.strokeRect(40 + 3 * 140 - 2, buttonY - 2, buttonWidth + 4, buttonHeight + 4)
      } else {
        // Default highlight on first button
        ctx.strokeRect(40 - 2, buttonY - 2, buttonWidth + 4, buttonHeight + 4)
      }
      ctx.setLineDash([])
      ctx.lineWidth = 1
      break
    }

    case 'type': {
      // Draw input form
      const formY = contentY + 120
      const inputWidth = 300
      const inputHeight = 36

      // Draw form container
      ctx.fillStyle = '#fafafa'
      ctx.fillRect(40, formY, width - 80, 200)
      ctx.strokeStyle = '#e8e8e8'
      ctx.strokeRect(40, formY, width - 80, 200)

      // Draw input field with label
      ctx.fillStyle = '#333'
      ctx.font = '14px Arial'
      ctx.fillText('输入框:', 60, formY + 30)

      ctx.fillStyle = '#fff'
      ctx.strokeStyle = '#409eff'
      ctx.lineWidth = 2
      ctx.fillRect(60, formY + 40, inputWidth, inputHeight)
      ctx.strokeRect(60, formY + 40, inputWidth, inputHeight)
      ctx.lineWidth = 1

      // Draw typed text
      if (action.text) {
        ctx.fillStyle = '#333'
        ctx.font = '14px Arial'
        ctx.fillText(action.text, 70, formY + 63)

        // Draw cursor
        const textWidth = ctx.measureText(action.text).width
        ctx.fillStyle = '#333'
        ctx.fillRect(70 + textWidth + 2, formY + 48, 2, 20)
      }

      // Draw another input field
      ctx.fillStyle = '#333'
      ctx.font = '14px Arial'
      ctx.fillText('密码:', 60, formY + 100)

      ctx.fillStyle = '#fff'
      ctx.strokeStyle = '#d0d0d0'
      ctx.fillRect(60, formY + 110, inputWidth, inputHeight)
      ctx.strokeRect(60, formY + 110, inputWidth, inputHeight)

      // Draw dots for password
      ctx.fillStyle = '#333'
      for (let i = 0; i < 6; i++) {
        ctx.beginPath()
        ctx.arc(80 + i * 15, formY + 128, 3, 0, Math.PI * 2)
        ctx.fill()
      }
      break
    }

    case 'keypress': {
      // Show keyboard action
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)

      // Draw keyboard icon
      ctx.fillStyle = '#666'
      ctx.font = '48px Arial'
      ctx.textAlign = 'center'
      ctx.fillText('⌨️', width / 2, contentY + 200)

      // Show key pressed
      ctx.fillStyle = '#333'
      ctx.font = '16px Arial'
      ctx.fillText(`按下按键: ${action.key || ''}`, width / 2, contentY + 250)
      ctx.textAlign = 'left'
      break
    }

    case 'scroll': {
      // Draw scrollable content
      ctx.fillStyle = '#fff'
      ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)
      ctx.strokeStyle = '#e0e0e0'
      ctx.strokeRect(20, contentY + 100, width - 40, contentHeight - 150)

      // Draw content blocks
      for (let i = 0; i < 5; i++) {
        ctx.fillStyle = i % 2 === 0 ? '#f5f5f5' : '#fff'
        ctx.fillRect(30, contentY + 110 + i * 50, width - 60, 45)
        ctx.fillStyle = '#666'
        ctx.font = '13px Arial'
        ctx.fillText(`内容块 ${i + 1}`, 50, contentY + 135 + i * 50)
      }

      // Draw scroll indicator
      const scrollDirection = (action.deltaY || 0) > 0 ? '↓' : '↑'
      ctx.fillStyle = '#409eff'
      ctx.font = '24px Arial'
      ctx.textAlign = 'center'
      ctx.fillText(scrollDirection, width - 40, contentY + 200)
      ctx.textAlign = 'left'

      // Draw scroll bar
      ctx.fillStyle = '#e0e0e0'
      ctx.fillRect(width - 30, contentY + 100, 10, contentHeight - 150)
      ctx.fillStyle = '#409eff'
      ctx.fillRect(width - 30, contentY + 120, 10, 40)
      break
    }

    case 'mousemove':
    case 'mousedown':
    case 'mouseup': {
      // Draw mouse cursor movement
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)

      // Draw some elements
      ctx.fillStyle = '#fff'
      ctx.fillRect(40, contentY + 130, 150, 100)
      ctx.strokeStyle = '#e0e0e0'
      ctx.strokeRect(40, contentY + 130, 150, 100)

      ctx.fillRect(220, contentY + 130, 150, 100)
      ctx.strokeRect(220, contentY + 130, 150, 100)

      // Draw cursor at position
      if (action.x !== undefined && action.y !== undefined) {
        // Scale coordinates to canvas
        const scaleX = width / 1920
        const scaleY = height / 1080
        const cursorX = action.x * scaleX
        const cursorY = action.y * scaleY

        // Draw cursor arrow
        ctx.fillStyle = action.type === 'mousedown' ? '#ff4d4f' : '#333'
        ctx.beginPath()
        ctx.moveTo(cursorX, cursorY)
        ctx.lineTo(cursorX, cursorY + 15)
        ctx.lineTo(cursorX + 5, cursorY + 12)
        ctx.lineTo(cursorX + 8, cursorY + 18)
        ctx.lineTo(cursorX + 11, cursorY + 16)
        ctx.lineTo(cursorX + 8, cursorY + 10)
        ctx.lineTo(cursorX + 12, cursorY + 10)
        ctx.closePath()
        ctx.fill()
      }
      break
    }

    default:
      // Default: show step text
      ctx.fillStyle = '#f0f0f0'
      ctx.fillRect(20, contentY + 100, width - 40, contentHeight - 150)
      ctx.fillStyle = '#666'
      ctx.font = '14px Arial'
      ctx.textAlign = 'center'
      ctx.fillText('执行操作中...', width / 2, contentY + 200)
      ctx.textAlign = 'left'
  }

  // Draw status bar
  ctx.fillStyle = '#f5f5f5'
  ctx.fillRect(0, height - 40, width, 40)
  ctx.strokeStyle = '#e0e0e0'
  ctx.strokeRect(0, height - 40, width, 40)
  ctx.fillStyle = '#666'
  ctx.font = '12px Arial'
  ctx.fillText('就绪', 10, height - 15)
}

function drawActionHighlight(ctx: CanvasRenderingContext2D, width: number, _height: number, action: { type: string; selector?: string; x?: number; y?: number }) {
  const indicatorX = width - 30
  const indicatorY = 55

  const colors: Record<string, string> = {
    'click': '#ff4d4f',
    'dblclick': '#ff4d4f',
    'type': '#52c41a',
    'keypress': '#722ed1',
    'goto': '#1890ff',
    'scroll': '#faad14',
    'mousemove': '#8c8c8c',
    'mousedown': '#ff4d4f',
    'mouseup': '#52c41a'
  }

  ctx.fillStyle = colors[action.type] || '#8c8c8c'
  ctx.beginPath()
  ctx.arc(indicatorX, indicatorY, 8, 0, Math.PI * 2)
  ctx.fill()

  ctx.fillStyle = '#333'
  ctx.font = '12px Arial'
  ctx.textAlign = 'right'

  const labels: Record<string, string> = {
    'click': '点击',
    'dblclick': '双击',
    'type': '输入',
    'keypress': '按键',
    'goto': '导航',
    'scroll': '滚动',
    'mousemove': '移动',
    'mousedown': '按下',
    'mouseup': '释放',
    'other': '执行'
  }

  ctx.fillText(labels[action.type] || '执行', indicatorX - 15, indicatorY + 4)
  ctx.textAlign = 'left'
}

function drawStepInfo(ctx: CanvasRenderingContext2D, width: number, height: number, step: string, currentStep: number, totalSteps: number) {
  const boxX = 20
  const boxY = height - 75
  const boxWidth = width - 40
  const boxHeight = 30

  // Draw info box background
  ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
  ctx.fillRect(boxX, boxY, boxWidth, boxHeight)

  // Draw step text
  ctx.fillStyle = '#fff'
  ctx.font = '13px Arial'
  const stepText = `步骤 ${currentStep + 1}/${totalSteps}: ${step}`
  const maxWidth = boxWidth - 20

  if (ctx.measureText(stepText).width > maxWidth) {
    let truncated = stepText
    while (ctx.measureText(truncated + '...').width > maxWidth && truncated.length > 0) {
      truncated = truncated.slice(0, -1)
    }
    ctx.fillText(truncated + '...', boxX + 10, boxY + 20)
  } else {
    ctx.fillText(stepText, boxX + 10, boxY + 20)
  }

  // Draw progress bar
  const progressBarY = height - 40
  const progressBarWidth = width - 40
  const progress = totalSteps > 0 ? (currentStep + 1) / totalSteps : 0

  ctx.fillStyle = '#e0e0e0'
  ctx.fillRect(boxX, progressBarY, progressBarWidth, 6)
  ctx.fillStyle = '#409eff'
  ctx.fillRect(boxX, progressBarY, progressBarWidth * progress, 6)
}

function pauseReplay() {
  replayStatus.value = 'paused'
}

function resumeReplay() {
  replayStatus.value = 'playing'
}

function stopReplay() {
  if (replayAbortController) {
    replayAbortController.abort()
    replayAbortController = null
  }
  replayStatus.value = 'idle'
  replayStep.value = 0
  ElMessage.info('回放已结束')
}

function handleReplayClose() {
  if (replayAbortController) {
    replayAbortController.abort()
    replayAbortController = null
  }
  replayStatus.value = 'idle'
  replayStep.value = 0
  selectedStep.value = null
  replayScript.value = ''
  replayCaseId.value = ''
  replaySteps.value = []
  recordedScreenshots = []
  recordedLineToAction = []
  replayScreenshotImages = []
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
.record-viewport { width: 100%; height: 60vh; background: #1a1a2e; border-radius: 8px; overflow: hidden; position: relative; display: flex; align-items: center; justify-content: center; user-select: none; }
.record-canvas { max-width: 100%; max-height: 100%; object-fit: contain; touch-action: none; pointer-events: auto; user-select: none; }
.record-placeholder { position: absolute; display: flex; flex-direction: column; align-items: center; gap: 12px; color: var(--el-text-color-secondary); }
.record-footer { display: flex; align-items: center; gap: 12px; margin-top: 12px; }
.record-indicator { display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--el-color-danger); font-weight: 600; }
.record-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--el-color-danger); animation: pulse 1s infinite; }
.frame-counter { font-size: 12px; color: var(--el-text-color-secondary); font-weight: 400; }
@keyframes pulse { 0%,100%{ opacity:1; } 50%{ opacity:0.3; } }

/* Assert context menu */
.assert-context-menu { position: absolute; z-index: 100; background: #fff; border-radius: 6px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); min-width: 150px; padding: 4px 0; }
.assert-menu-title { padding: 8px 16px; font-size: 12px; color: #999; border-bottom: 1px solid #eee; }
.assert-menu-item { padding: 8px 16px; font-size: 13px; cursor: pointer; white-space: nowrap; }
.assert-menu-item:hover { background: #f0f5ff; color: #1890ff; }

/* Replay styles */
.replay-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.replay-viewport { width: 100%; height: 60vh; background: #f5f5f5; border-radius: 8px; overflow: hidden; position: relative; }
.replay-content { display: flex; height: 100%; }
.replay-steps { width: 300px; border-right: 1px solid #e0e0e0; display: flex; flex-direction: column; background: #fff; }
.replay-steps-header { padding: 12px 16px; font-weight: 600; border-bottom: 1px solid #e0e0e0; background: #fafafa; }
.replay-steps-list { flex: 1; overflow-y: auto; padding: 8px; }
.replay-step-item { display: flex; align-items: flex-start; gap: 8px; padding: 8px; border-radius: 4px; margin-bottom: 4px; }
.replay-step-item.active { background: #e6f7ff; border: 1px solid #91d5ff; }
.replay-step-item.completed { opacity: 0.6; }
.step-number { width: 24px; height: 24px; border-radius: 50%; background: #d9d9d9; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
.replay-step-item.active .step-number { background: #1890ff; color: #fff; }
.replay-step-item.completed .step-number { background: #52c41a; color: #fff; }
.replay-step-item.clickable { cursor: pointer; }
.replay-step-item.clickable:hover { background: #f5f7fa; }
.replay-step-item.selected { background: #f0f5ff; border-left: 3px solid #1890ff; }
.step-content { flex: 1; font-size: 13px; word-break: break-all; }
.replay-preview { flex: 1; display: flex; flex-direction: column; }
.replay-preview-header { padding: 12px 16px; font-weight: 600; border-bottom: 1px solid #e0e0e0; background: #fafafa; }
.replay-preview-content { flex: 1; position: relative; display: flex; align-items: center; justify-content: center; padding: 16px; }
.replay-canvas { border: 1px solid #e0e0e0; border-radius: 4px; background: #fff; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1); display: block; }
.replay-placeholder { position: absolute; display: flex; flex-direction: column; align-items: center; gap: 12px; color: var(--el-text-color-secondary); }
.replay-indicator { position: absolute; top: 16px; right: 16px; display: flex; align-items: center; gap: 8px; font-size: 14px; color: var(--el-color-primary); font-weight: 600; background: rgba(255,255,255,0.9); padding: 8px 16px; border-radius: 8px; }
.replay-indicator.paused { color: var(--el-color-danger); }
.replay-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--el-color-primary); animation: pulse 1s infinite; }
.replay-dot.paused { background: var(--el-color-danger); animation: none; }
.replay-finished { position: absolute; display: flex; flex-direction: column; align-items: center; gap: 12px; }
.replay-finished p { color: var(--el-color-success); font-size: 16px; font-weight: 600; }
.replay-footer { margin-top: 12px; }
</style>
