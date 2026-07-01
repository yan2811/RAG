/**
 * 文档管理相关 API（M1 模块）
 */
import request from '@/utils/request'

/** 上传 PDF 文档 */
export function uploadDocumentApi(formData: FormData) {
  return request.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,  // 上传+解析可能需要较长时间，5 分钟超时
  })
}

/** 获取文档列表 */
export function getDocumentsApi(params?: any) {
  return request.get('/documents', { params })
}

/** 获取文档详情（含分块列表） */
export function getDocumentDetailApi(id: number) {
  return request.get(`/documents/${id}`)
}

/** 删除文档（软删除） */
export function deleteDocumentApi(id: number) {
  return request.delete(`/documents/${id}`)
}

/** 查询文档解析进度 */
export function getParseStatusApi(id: number) {
  return request.get(`/documents/${id}/status`)
}

/** 手动触发文档重新解析 */
export function triggerParseApi(id: number) {
  return request.post(`/documents/${id}/parse`, null, { timeout: 120000 })
}
