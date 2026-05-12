import request from '@/utils/request'

export interface SystemLogItem {
  id: string
  user_id: string | null
  operation: string
  resource_type: string
  resource_id: string | null
  description: string | null
  created_at: string
}

export interface NotificationItem {
  id: string
  title: string
  content: string
  is_read: boolean
  created_at: string
}

export function getSystemLogs(params: any) {
  return request.get<any, any>('/system/logs', { params })
}

export function getNotifications(params: any) {
  return request.get<any, any>('/system/notifications', { params })
}

export function markNotificationRead(id: string) {
  return request.put(`/system/notifications/${id}/read`)
}

export function getSystemConfig() {
  return request.get('/system/config')
}

export function updateSystemConfig(data: any) {
  return request.put('/system/config', data)
}

export function getSystemStats() {
  return request.get('/system/stats')
}
