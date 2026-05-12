import request from '@/utils/request'

export function getCaseList(params: any) {
  return request.get('/cases', { params })
}

export function getCaseDetail(id: string) {
  return request.get(`/cases/${id}`)
}

export function getCaseAuthors() {
  return request.get('/cases/authors')
}

export function createCase(data: any) {
  return request.post('/cases', data)
}

export function updateCase(id: string, data: any) {
  return request.put(`/cases/${id}`, data)
}

export function deleteCase(id: string) {
  return request.delete(`/cases/${id}`)
}

export function updateCaseStatus(id: string, status: string) {
  return request.put(`/cases/${id}`, { status })
}

export function exportCases(params: any) {
  return request.get('/cases/export', { params, responseType: 'blob' })
}
