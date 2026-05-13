import request from '@/utils/request'

// Case CRUD
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

export function executeCases(caseIds: string[]) {
  return request.post('/cases/execute', { case_ids: caseIds })
}

export function copyCase(id: string) {
  return request.post(`/cases/${id}/copy`)
}

// Folder CRUD
export function getFolderTree() {
  return request.get('/cases/folders/tree')
}

export function createFolder(data: { name: string; parent_id?: string }) {
  return request.post('/cases/folders', data)
}

export function updateFolder(id: string, data: { name?: string; parent_id?: string }) {
  return request.put(`/cases/folders/${id}`, data)
}

export function deleteFolder(id: string) {
  return request.delete(`/cases/folders/${id}`)
}

export function copyFolder(id: string) {
  return request.post(`/cases/folders/${id}/copy`)
}

// Trash
export function getTrashList() {
  return request.get('/cases/trash')
}

export function emptyTrash() {
  return request.post('/cases/trash/empty')
}

export function restoreTrashItem(itemType: string, itemId: string) {
  return request.post(`/cases/trash/restore/${itemType}/${itemId}`)
}
