<template>
  <div class="user-management">
    <div class="toolbar">
      <el-input v-model="keyword" placeholder="搜索用户名/邮箱/姓名" clearable style="width:260px" @clear="fetchUsers" @keyup.enter="fetchUsers">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-button type="primary" @click="showAddDialog">新增用户</el-button>
    </div>

    <el-table :data="users" v-loading="loading" stripe border>
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="email" label="邮箱" min-width="180" show-overflow-tooltip />
      <el-table-column prop="real_name" label="真实姓名" width="120" />
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{row}">
          <el-tag :type="roleTagType(row.role)" size="small">{{ row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80">
        <template #default="{row}">
          <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">{{ row.is_active ? '正常' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_login_at" label="最后登录" width="170" />
      <el-table-column prop="created_at" label="创建时间" width="170" />
      <el-table-column label="操作" width="200" fixed="right">
        <template #default="{row}">
          <el-button link type="primary" size="small" @click="showResetDialog(row)">重置密码</el-button>
          <el-button link :type="row.is_active ? 'danger' : 'success'" size="small" @click="handleToggleActive(row)">{{ row.is_active ? '禁用' : '启用' }}</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination class="pagination" v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" layout="total, prev, pager, next" @current-change="fetchUsers" />

    <!-- 新增用户对话框 -->
    <el-dialog v-model="addDialogVisible" title="新增用户" width="460px" destroy-on-close>
      <el-form ref="addFormRef" :model="addForm" :rules="addRules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="addForm.username" placeholder="3-64个字符" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input v-model="addForm.password" type="password" placeholder="至少8位" show-password />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="addForm.email" placeholder="邮箱地址" />
        </el-form-item>
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="addForm.real_name" placeholder="选填" />
        </el-form-item>
        <el-form-item label="角色" prop="role_code">
          <el-select v-model="addForm.role_code" style="width:100%">
            <el-option label="测试人员 (TESTER)" value="TESTER" />
            <el-option label="运维人员 (OPS)" value="OPS" />
            <el-option label="管理员 (ADMIN)" value="ADMIN" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleAddUser">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetDialogVisible" title="重置密码" width="400px" destroy-on-close>
      <el-form ref="resetFormRef" :model="resetForm" :rules="resetRules" label-width="80px">
        <el-form-item label="用户">
          <el-input :model-value="resetTarget?.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="resetForm.new_password" type="password" placeholder="至少8位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleResetPassword">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { getUsers, createUser, resetUserPassword, toggleUserActive } from '@/api/users'

const users = ref<any[]>([])
const loading = ref(false)
const submitting = ref(false)
const keyword = ref('')
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

// Add user dialog
const addDialogVisible = ref(false)
const addFormRef = ref()
const addForm = reactive({ username: '', password: '', email: '', real_name: '', role_code: 'TESTER' })
const addRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, max: 64, message: '长度3-64', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 8, max: 128, message: '长度8-128', trigger: 'blur' }],
  email: [{ required: true, message: '请输入邮箱', trigger: 'blur' }, { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }],
  role_code: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

// Reset password dialog
const resetDialogVisible = ref(false)
const resetFormRef = ref()
const resetTarget = ref<any>(null)
const resetForm = reactive({ new_password: '' })
const resetRules = {
  new_password: [{ required: true, message: '请输入新密码', trigger: 'blur' }, { min: 8, max: 128, message: '长度8-128', trigger: 'blur' }],
}

function roleTagType(role: string) {
  if (role === 'ADMIN') return 'danger'
  if (role === 'OPS') return 'warning'
  return 'info'
}

async function fetchUsers() {
  loading.value = true
  try {
    const params: any = { page: pagination.page, pageSize: pagination.pageSize }
    if (keyword.value) params.keyword = keyword.value
    const res = await getUsers(params)
    users.value = res.data?.list || []
    pagination.total = res.data?.pagination?.total || 0
  } catch {} finally { loading.value = false }
}

function showAddDialog() {
  Object.assign(addForm, { username: '', password: '', email: '', real_name: '', role_code: 'TESTER' })
  addDialogVisible.value = true
}

async function handleAddUser() {
  const valid = await addFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await createUser(addForm)
    ElMessage.success('用户创建成功')
    addDialogVisible.value = false
    fetchUsers()
  } catch {} finally { submitting.value = false }
}

function showResetDialog(row: any) {
  resetTarget.value = row
  resetForm.new_password = ''
  resetDialogVisible.value = true
}

async function handleResetPassword() {
  const valid = await resetFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await resetUserPassword(resetTarget.value.id, { new_password: resetForm.new_password })
    ElMessage.success('密码重置成功')
    resetDialogVisible.value = false
  } catch {} finally { submitting.value = false }
}

async function handleToggleActive(row: any) {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}用户 "${row.username}" 吗？`, '提示', { type: 'warning' })
    await toggleUserActive(row.id, { is_active: !row.is_active })
    ElMessage.success(`用户已${action}`)
    fetchUsers()
  } catch {}
}

onMounted(() => fetchUsers())
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
