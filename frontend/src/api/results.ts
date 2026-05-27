import request from '@/utils/request'

export interface ResultOverview {
  totalCases: number
  successCount: number
  failedCount: number
  skippedCount: number
  successRate: number
  duration: number
}

export interface ResultItem {
  id: string
  task_id: string
  case_id: string
  caseName: string
  caseType: string
  status: string
  duration: number
  startedAt: string | null
  finishedAt: string | null
}

export interface ResultDetail {
  id: string
  task_id: string
  case_id: string
  case_name: string
  case_type: string
  status: string
  detail: any
  duration_ms: number
}

export type ResultStatus = 'SUCCESS' | 'FAILED' | 'SKIPPED'

export function getResultOverview(taskId: string) {
  return request.get<any, any>('/results/overview', { params: { taskId } })
}

export function getResultList(params: any) {
  return request.get<any, any>('/results', { params })
}

export function getResultDetail(resultId: string) {
  return request.get<any, any>(`/results/api/${resultId}`)
}

export function exportResults(taskId: string, format: string) {
  return request.post(`/results/${taskId}/export`, { format })
}

export function createShareLink(taskId: string, data: any) {
  return request.post<any, any>(`/results/${taskId}/share`, data)
}

export function syncPerfScript(caseId: string) {
  return request.post<any, any>(`/results/sync-perf-script/${caseId}`)
}
