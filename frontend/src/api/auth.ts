import request from '@/utils/request'

export function login(data: { username: string; password: string }) {
  return request.post<any, any>('/auth/login', data)
}

export function register(data: { username: string; password: string; email: string; real_name?: string }) {
  return request.post<any, any>('/auth/register', data)
}

export function logout() {
  return request.post('/auth/logout')
}

export function refreshToken() {
  return request.post('/auth/refresh-token')
}

export function getMe() {
  return request.get('/auth/me')
}
