/**
 * 知识库管理相关 API（M2+M3 模块）
 */
import request from '@/utils/request'

/** 知识库概览统计 */
export function getOverviewApi() {
  return request.get('/knowledge/overview')
}

/** 知识库详细统计 */
export function getStatsApi() {
  return request.get('/knowledge/stats')
}

/** 获取标签列表 */
export function getTagsApi() {
  return request.get('/knowledge/tags')
}

/** 创建标签 */
export function createTagApi(name: string, color?: string, description?: string) {
  return request.post('/knowledge/tags', { name, color, description })
}

/** 删除标签 */
export function deleteTagApi(id: number) {
  return request.delete(`/knowledge/tags/${id}`)
}

/** 为文档添加标签 */
export function setDocTagsApi(docId: number, tagIds: number[]) {
  return request.post(`/knowledge/documents/${docId}/tags`, tagIds)
}

/** 构建文档向量索引 */
export function buildIndexApi(docId: number) {
  return request.post(`/knowledge/index/${docId}`)
}

/** 全量重建向量索引 */
export function reindexAllApi() {
  return request.post('/knowledge/reindex')
}
