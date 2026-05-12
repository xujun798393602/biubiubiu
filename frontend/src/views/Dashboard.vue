<template>
  <div class="dashboard">
    <el-row :gutter="20" class="stat-row">
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="测试用例" :value="stats.totalCases" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="测试任务" :value="stats.totalTasks" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="测试节点" :value="stats.totalNodes" /></el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover"><el-statistic title="在线节点" :value="onlineNodes" /></el-card>
      </el-col>
    </el-row>
    <el-row :gutter="20">
      <el-col :span="12">
        <el-card header="最近任务">
          <el-table :data="recentTasks" stripe size="small">
            <el-table-column prop="name" label="任务名称" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}"><el-tag :type="row.status==='SUCCESS'?'success':row.status==='FAILED'?'danger':'info'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card header="节点状态">
          <el-table :data="nodes" stripe size="small">
            <el-table-column prop="name" label="节点" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}"><el-tag :type="row.status==='ONLINE'?'success':'danger'" size="small">{{ row.status }}</el-tag></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getSystemStats } from '@/api/system'
import { getTaskList } from '@/api/tasks'
import { getNodeList } from '@/api/nodes'
import type { TaskItem } from '@/api/tasks'
import type { NodeItem } from '@/api/nodes'

const stats = ref({ totalCases: 0, totalTasks: 0, totalNodes: 0 })
const recentTasks = ref<TaskItem[]>([])
const nodes = ref<NodeItem[]>([])
const onlineNodes = ref(0)

onMounted(async () => {
  try { const res = await getSystemStats(); stats.value = res.data } catch {}
  try { const res = await getTaskList({ page:1, pageSize:5 }); recentTasks.value = res.data?.list || [] } catch {}
  try {
    const res = await getNodeList({ page:1, pageSize:100 })
    nodes.value = res.data?.list || []
    onlineNodes.value = nodes.value.filter(n => n.status === 'ONLINE').length
  } catch {}
})
</script>

<style scoped>
.stat-row { margin-bottom:20px; }
</style>
