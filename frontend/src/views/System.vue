<template>
  <div class="system">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="操作日志" name="logs">
        <el-table :data="logs" v-loading="logsLoading" stripe border>
          <el-table-column prop="operation" label="操作" width="100" />
          <el-table-column prop="resource_type" label="资源类型" width="100" />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="170" />
        </el-table>
        <el-pagination class="pagination" v-model:current-page="logPagination.page" v-model:page-size="logPagination.pageSize" :total="logPagination.total" layout="total, prev, pager, next" @current-change="fetchLogs" />
      </el-tab-pane>
      <el-tab-pane label="通知" name="notifications">
        <el-table :data="notifications" v-loading="notiLoading" stripe border>
          <el-table-column prop="title" label="标题" min-width="200" />
          <el-table-column prop="content" label="内容" min-width="300" show-overflow-tooltip />
          <el-table-column prop="is_read" label="状态" width="80"><template #default="{row}"><el-tag :type="row.is_read?'info':'danger'" size="small">{{ row.is_read?'已读':'未读' }}</el-tag></template></el-table-column>
          <el-table-column prop="created_at" label="时间" width="170" />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSystemLogs, getNotifications } from '@/api/system'
import type { SystemLogItem, NotificationItem } from '@/api/system'

const activeTab = ref('logs')
const logs = ref<SystemLogItem[]>([])
const notifications = ref<NotificationItem[]>([])
const logsLoading = ref(false)
const notiLoading = ref(false)
const logPagination = reactive({ page: 1, pageSize: 20, total: 0 })

async function fetchLogs() {
  logsLoading.value = true
  try {
    const res = await getSystemLogs({ page: logPagination.page, pageSize: logPagination.pageSize })
    logs.value = res.data?.list || []
    logPagination.total = res.data?.pagination?.total || 0
  } catch {} finally { logsLoading.value = false }
}

async function fetchNotifications() {
  notiLoading.value = true
  try {
    const res = await getNotifications({ page: 1, pageSize: 50 })
    notifications.value = res.data?.list || []
  } catch {} finally { notiLoading.value = false }
}

onMounted(() => { fetchLogs(); fetchNotifications() })
</script>

<style scoped>
.pagination { margin-top:16px; display:flex; justify-content:flex-end; }
</style>
