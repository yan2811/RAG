/**
 * 系统管理相关 API（M9 模块）
 */
import request from '@/utils/request'

// ===== 用户管理 =====
export function getUsersApi(params?: any) {
  return request.get('/admin/users', { params })
}
export function createUserApi(data: any) {
  return request.post('/admin/users', data)
}
export function updateUserApi(id: number, data: any) {
  return request.put(`/admin/users/${id}`, data)
}
export function deleteUserApi(id: number) {
  return request.delete(`/admin/users/${id}`)
}

// ===== 角色管理 =====
export function getRolesApi() {
  return request.get('/admin/roles')
}
export function createRoleApi(data: any) {
  return request.post('/admin/roles', data)
}

// ===== 操作日志 =====
export function getLogsApi(params?: any) {
  return request.get('/admin/logs', { params })
}

// ===== 系统配置 =====
export function getSettingsApi() {
  return request.get('/admin/settings')
}
export function updateSettingsApi(data: any) {
  return request.put('/admin/settings', data)
}
