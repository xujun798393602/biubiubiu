<template>
  <div class="node-list">
    <el-card>
      <template #header>
        <div class="card-header"><span>节点管理</span><el-button type="primary" icon="Plus" @click="handleCreate">添加节点</el-button></div>
      </template>
      <el-table :data="nodeList" v-loading="loading" stripe border>
        <el-table-column prop="name" label="节点名称" min-width="150" />
        <el-table-column prop="host" label="地址" min-width="200" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="status" label="状态" width="100"><template #default="{row}"><el-tag :type="row.status==='ONLINE'?'success':row.status==='ERROR'?'danger':'info'" size="small">{{ row.status }}</el-tag></template></el-table-column>
        <el-table-column prop="cpu_usage" label="CPU" width="80"><template #default="{row}">{{ row.cpu_usage ?? '-' }}%</template></el-table-column>
        <el-table-column prop="memory_usage" label="内存" width="80"><template #default="{row}">{{ row.memory_usage ?? '-' }}%</template></el-table-column>
        <el-table-column prop="current_tasks" label="任务数" width="80" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{row}">
            <el-button text type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
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
import { ElMessage } from 'element-plus'
import { getNodeList, deleteNode, updateNodeStatus } from '@/api/nodes'
import type { NodeItem, NodeStatus } from '@/api/nodes'

const loading = ref(false)
const nodeList = ref<NodeItem[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

async function fetchData() {
  loading.value = true
  try {
    const res = await getNodeList({ page: pagination.page, pageSize: pagination.pageSize })
    nodeList.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

function handleCreate() { ElMessage.info('添加节点功能待实现') }
function handleEdit(row: NodeItem) { ElMessage.info(`编辑节点: ${row.name}`) }
async function handleDelete(id: string) { try { await deleteNode(id); ElMessage.success('删除成功'); fetchData() } catch {} }

onMounted(fetchData)
</script>

<style scoped>
.card-header { display:flex; align-items:center; justify-content:space-between; }
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }
</style>
