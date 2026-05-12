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
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{row}">
            <el-button text type="primary" size="small" @click="handleStart(row)" :disabled="row.status==='RUNNING'">启动</el-button>
            <el-button text type="warning" size="small" @click="handleCancel(row)" :disabled="row.status!=='RUNNING'">取消</el-button>
            <el-button text type="primary" size="small" @click="router.push(`/results?taskId=${row.id}`)">结果</el-button>
            <el-popconfirm title="确认删除?" @confirm="handleDelete(row.id)"><template #reference><el-button text type="danger" size="small">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10,20,50]" layout="total, sizes, prev, pager, next" @size-change="fetchData" @current-change="fetchData" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getTaskList, deleteTask, startTask, cancelTask } from '@/api/tasks'
import type { TaskItem, TaskStatus, TaskPriority } from '@/api/tasks'

const router = useRouter()
const loading = ref(false)
const taskList = ref<TaskItem[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

async function fetchData() {
  loading.value = true
  try {
    const res = await getTaskList({ page: pagination.page, pageSize: pagination.pageSize })
    taskList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

function handleCreate() { ElMessage.info('新建任务功能待实现') }
async function handleStart(row: TaskItem) { try { await startTask(row.id); ElMessage.success('任务已启动'); fetchData() } catch {} }
async function handleCancel(row: TaskItem) { try { await cancelTask(row.id); ElMessage.success('任务已取消'); fetchData() } catch {} }
async function handleDelete(id: string) { try { await deleteTask(id); ElMessage.success('删除成功'); fetchData() } catch {} }

onMounted(fetchData)
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }
</style>
