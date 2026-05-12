<template>
  <el-container class="layout-container">
    <el-aside width="200px" class="layout-aside">
      <div class="logo">自动化测试平台</div>
      <el-menu :default-active="route.path" router class="layout-menu">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon><span>仪表盘</span></el-menu-item>
        <el-menu-item index="/cases"><el-icon><Document /></el-icon><span>用例管理</span></el-menu-item>
        <el-menu-item index="/tasks"><el-icon><List /></el-icon><span>任务管理</span></el-menu-item>
        <el-menu-item index="/results"><el-icon><DataAnalysis /></el-icon><span>结果展示</span></el-menu-item>
        <el-menu-item index="/nodes"><el-icon><Monitor /></el-icon><span>节点管理</span></el-menu-item>
        <el-menu-item index="/system"><el-icon><Setting /></el-icon><span>系统管理</span></el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="layout-header">
        <span>{{ route.name }}</span>
        <div class="header-right">
          <el-badge :value="unreadCount" :hidden="!unreadCount" class="notification-badge">
            <el-icon :size="20" style="cursor:pointer" @click="showNotifications=true"><Bell /></el-icon>
          </el-badge>
          <el-dropdown @command="handleCommand">
            <span class="user-info">{{ authStore.username }} <el-icon><ArrowDown /></el-icon></span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      <el-main class="layout-main"><router-view /></el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getNotifications } from '@/api/system'

const route = useRoute()
const authStore = useAuthStore()
const unreadCount = ref(0)
const showNotifications = ref(false)

function handleCommand(cmd: string) {
  if (cmd === 'logout') authStore.logout()
}

onMounted(async () => {
  try {
    const res = await getNotifications({ page: 1, pageSize: 1 })
    unreadCount.value = res.data?.list?.filter((n: any) => !n.is_read).length || 0
  } catch {}
})
</script>

<style scoped>
.layout-container { height:100vh; }
.layout-aside { background:#304156; }
.logo { height:60px; display:flex; align-items:center; justify-content:center; color:#fff; font-size:16px; font-weight:bold; }
.layout-menu { border-right:none; background:#304156; }
.layout-menu .el-menu-item { color:#bfcbd9; }
.layout-menu .el-menu-item.is-active { color:#409eff; background:#263445; }
.layout-header { display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid #e6e6e6; background:#fff; }
.header-right { display:flex; align-items:center; gap:16px; }
.user-info { display:flex; align-items:center; gap:4px; cursor:pointer; }
.notification-badge { display:flex; align-items:center; }
.layout-main { background:#f0f2f5; padding:20px; }
</style>
