import request from '@/utils/request'

export interface TaskItem {
  id: string
  name: string
  status: string
  priority: string
  creator_id: string
  total_cases: number
  success_count: number
  failed_count: number
  skipped_count: number
}

export type TaskStatus = 'PENDING' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CANCELLED'
export type TaskPriority = 'HIGH' | 'MEDIUM' | 'LOW'

export function getTaskList(params: any) {
  return request.get('/tasks', { params })
}

export function getTaskDetail(id: string) {
  return request.get(`/tasks/${id}`)
}

export function createTask(data: any) {
  return request.post('/tasks', data)
}

export function updateTask(id: string, data: any) {
  return request.put(`/tasks/${id}`, data)
}

export function deleteTask(id: string) {
  return request.delete(`/tasks/${id}`)
}

export function startTask(id: string) {
  return request.post(`/tasks/${id}/start`)
}

export function cancelTask(id: string) {
  return request.post(`/tasks/${id}/cancel`)
}

export function getTaskLogs(id: string) {
  return request.get(`/tasks/${id}/logs`)
}
