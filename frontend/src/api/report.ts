/**
 * 报告与仪表盘 API（M6+M7）
 */
import request from '@/utils/request'

/** 生成报告 */
export function generateReportApi(data: { company_code: string; fiscal_year: number; report_type?: string; document_ids?: string }) {
  return request.post('/reports/generate', null, { params: data, timeout: 300000 })
}

/** 获取报告列表 */
export function getReportsApi(params?: any) {
  return request.get('/reports', { params })
}

/** 获取报告详情（含 Markdown） */
export function getReportDetailApi(id: number) {
  return request.get(`/reports/${id}`)
}

/** 删除报告 */
export function deleteReportApi(id: number) {
  return request.delete(`/reports/${id}`)
}

/** 下载报告 PDF */
export function downloadReportUrl(id: number) {
  const token = localStorage.getItem('token') || ''
  return `/api/v1/reports/${id}/download?token=${token}`
}

/** 获取仪表盘数据 */
export function getDashboardApi(docId: number) {
  return request.get(`/dashboard/${docId}`)
}

/** 获取文档指标 */
export function getMetricsApi(docId: number) {
  return request.get(`/dashboard/${docId}/metrics`)
}

/** AI 智能图表生成 */
export function generateAiChartsApi(docId: number, refresh: boolean = false) {
  return request.post(`/dashboard/${docId}/ai-charts?refresh=${refresh}`, null, { timeout: 180000 })
}

/** 跨公司对比 */
export function compareCompaniesApi(companyCodes: string, fiscalYear: number) {
  return request.get('/dashboard/compare', { params: { company_codes: companyCodes, fiscal_year: fiscalYear } })
}

/** 多步推理分析 */
export function agentAnalyzeApi(question: string, documentIds?: string) {
  return request.post('/agent/analyze', null, { params: { question, document_ids: documentIds }, timeout: 300000 })
}
