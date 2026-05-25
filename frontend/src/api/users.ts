import request from '@/utils/request'

export function getUsers(params: any) {
  return request.get<any, any>('/users', { params })
}

export function createUser(data: { username: string; password: string; email: string; real_name?: string; role_code?: string }) {
  return request.post<any, any>('/users', data)
}

export function resetUserPassword(userId: string, data: { new_password: string }) {
  return request.put<any, any>(`/users/${userId}/reset-password`, data)
}

export function toggleUserActive(userId: string, data: { is_active: boolean }) {
  return request.put<any, any>(`/users/${userId}/toggle-active`, data)
}
