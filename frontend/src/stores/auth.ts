import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, logout as logoutApi, refreshToken as refreshTokenApi } from '@/api/auth'
import router from '@/router'

export interface UserInfo {
  id: string
  username: string
  role: 'ADMIN' | 'TESTER' | 'OPS'
  permissions: string[]
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(
    localStorage.getItem('user') ? JSON.parse(localStorage.getItem('user')!) : null
  )

  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const userRole = computed(() => user.value?.role || '')

  async function login(username: string, password: string) {
    const res = await loginApi({ username, password })
    const data = res.data
    token.value = data.token
    user.value = data.user as UserInfo
    localStorage.setItem('token', data.token)
    localStorage.setItem('user', JSON.stringify(data.user))
    return data
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {}
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  async function refresh() {
    const res = await refreshTokenApi()
    const data = res.data
    token.value = data.token
    localStorage.setItem('token', data.token)
    return data
  }

  return { token, user, isLoggedIn, username, userRole, login, logout, refresh }
})
