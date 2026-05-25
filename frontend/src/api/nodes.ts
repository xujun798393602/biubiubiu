import request from '@/utils/request'

export interface NodeItem {
  id: string
  name: string
  host: string
  port: number
  status: string
  node_type: string
  cpu_usage: number | null
  memory_usage: number | null
  disk_usage: number | null
  current_tasks: number
  max_concurrent: number
  capabilities: Record<string, any> | null
  agent_version: string | null
  last_heartbeat_at: string | null
}

export type NodeStatus = 'ONLINE' | 'OFFLINE' | 'BUSY' | 'ERROR'
export type NodeType = 'PLAYWRIGHT' | 'LOCUST' | 'MIXED'

export interface NodeStats {
  total_nodes: number
  online_nodes: number
  offline_nodes: number
  busy_nodes: number
  error_nodes: number
  by_type: Record<string, number>
  total_tasks_running: number
  total_max_concurrent: number
  queue_depth: Record<string, number>
}

export interface NodeCreateData {
  name: string
  host: string
  port?: number
  node_type?: NodeType
  group_id?: string
  max_concurrent?: number
  capabilities?: Record<string, any>
}

export interface NodeScaleData extends NodeCreateData {
  count: number
}

// ── Node CRUD ──────────────────────────────────────────────────

export function getNodeList(params: any) {
  return request.get<any, any>('/nodes', { params })
}

export function getNodeDetail(id: string) {
  return request.get<any, any>(`/nodes/${id}`)
}

export function createNode(data: NodeCreateData) {
  return request.post<any, any>('/nodes', data)
}

export function updateNode(id: string, data: any) {
  return request.put<any, any>(`/nodes/${id}`, data)
}

export function deleteNode(id: string) {
  return request.delete<any, any>(`/nodes/${id}`)
}

export function updateNodeStatus(id: string, status: string) {
  return request.put<any, any>(`/nodes/${id}`, { status })
}

// ── Node Statistics ────────────────────────────────────────────

export function getNodeStats() {
  return request.get<any, any>('/nodes/stats')
}

// ── Node Scaling ───────────────────────────────────────────────

export function scaleNodes(data: NodeScaleData) {
  return request.post<any, any>('/nodes/scale', data)
}

// ── API Key Management ─────────────────────────────────────────

export function regenerateApiKey(id: string) {
  return request.post<any, any>(`/nodes/${id}/api-key`)
}

// ── Node Groups ────────────────────────────────────────────────

export function getNodeGroups() {
  return request.get<any, any>('/nodes/groups')
}

export function createNodeGroup(data: { name: string; description?: string }) {
  return request.post<any, any>('/nodes/groups', data)
}
