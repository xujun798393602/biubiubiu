import request from '@/utils/request'

export interface NodeItem {
  id: string
  name: string
  host: string
  port: number
  status: string
  cpu_usage: number | null
  memory_usage: number | null
  current_tasks: number
}

export type NodeStatus = 'ONLINE' | 'OFFLINE' | 'BUSY' | 'ERROR'

export function getNodeList(params: any) {
  return request.get<any, any>('/nodes', { params })
}

export function getNodeDetail(id: string) {
  return request.get(`/nodes/${id}`)
}

export function createNode(data: any) {
  return request.post('/nodes', data)
}

export function updateNode(id: string, data: any) {
  return request.put(`/nodes/${id}`, data)
}

export function deleteNode(id: string) {
  return request.delete(`/nodes/${id}`)
}

export function updateNodeStatus(id: string, status: string) {
  return request.put(`/nodes/${id}`, { status })
}
