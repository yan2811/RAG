<!--
  报告中心（M6）
  支持选择文档生成报告、批量导出、PDF下载
-->
<template>
  <div class="reports-page">
    <!-- 操作栏 -->
    <el-card style="margin-bottom: 16px;">
      <el-button type="primary" @click="openGenerateDialog">
        <el-icon><DocumentAdd /></el-icon>生成新报告
      </el-button>
      <el-button :disabled="selectedIds.length === 0" @click="handleBatchExport">
        <el-icon><Download /></el-icon>批量导出 ({{ selectedIds.length }})
      </el-button>
      <el-button :disabled="selectedIds.length === 0" type="danger" @click="handleBatchDelete">
        <el-icon><Delete /></el-icon>批量删除
      </el-button>
    </el-card>

    <!-- 报告列表 -->
    <el-card>
      <el-table :data="reports" border stripe v-loading="loading"
        @selection-change="onSelectionChange" ref="tableRef">
        <el-table-column type="selection" width="45" />
        <el-table-column prop="company_name" label="公司" min-width="160" />
        <el-table-column prop="company_code" label="股票代码" width="100" />
        <el-table-column prop="fiscal_year" label="财年" width="70" />
        <el-table-column label="类型" width="80">
          <template #default="{ row }">{{ typeMap[row.report_type] || '-' }}</template>
        </el-table-column>
        <el-table-column prop="created_at" label="生成时间" width="170">
          <template #default="{ row }">{{ row.created_at?.substring(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="viewReport(row)">预览</el-button>
            <el-button link size="small" @click="downloadReport(row)">下载PDF</el-button>
            <el-button link size="small" @click="downloadMarkdown(row)">导出MD</el-button>
            <el-button type="danger" link size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!loading && reports.length === 0" description="暂无报告">
        <el-button type="primary" @click="openGenerateDialog">生成第一份报告</el-button>
      </el-empty>
    </el-card>

    <!-- 生成报告对话框 -->
    <el-dialog v-model="dialogVisible" title="生成财务分析报告" width="560px" @closed="resetGenForm">
      <el-form label-width="80px">
        <el-form-item label="选择文档">
          <el-select v-model="genForm.docIds" multiple placeholder="选择知识库中的文档（可多选）"
            collapse-tags collapse-tags-tooltip style="width: 100%;">
            <el-option v-for="doc in availableDocs" :key="doc.id"
              :label="`${doc.file_name}（${doc.company_code || '-'}·${doc.fiscal_year || '-'}）`"
              :value="doc.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="股票代码">
          <el-input v-model="genForm.company_code" placeholder="如 002594，选中文档后自动填充" />
        </el-form-item>
        <el-form-item label="财年">
          <el-input-number v-model="genForm.fiscal_year" :min="2000" :max="2030" />
        </el-form-item>
        <el-form-item label="报告类型">
          <el-select v-model="genForm.report_type">
            <el-option value="annual" label="年报分析" />
            <el-option value="quarterly" label="季报分析" />
            <el-option value="comparison" label="对比分析" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="handleGenerate">
          {{ generating ? 'AI 报告生成中...' : '生成报告' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 报告预览 -->
    <el-dialog v-model="previewVisible" title="报告预览" width="860px" top="3vh">
      <div class="markdown-body" v-html="renderPreview(previewContent)" style="max-height: 72vh; overflow-y: auto;" />
      <template #footer>
        <el-button @click="previewVisible = false">关闭</el-button>
        <el-button type="primary" @click="downloadReport(previewReport)">下载PDF</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getReportsApi, generateReportApi, getReportDetailApi, deleteReportApi, downloadReportUrl } from '@/api/report'
import { getDocumentsApi } from '@/api/document'
import request from '@/utils/request'

const reports = ref<any[]>([])
const loading = ref(false)
const selectedIds = ref<number[]>([])

const dialogVisible = ref(false)
const generating = ref(false)
const previewVisible = ref(false)
const previewContent = ref('')
const previewReport = ref<any>(null)

const availableDocs = ref<any[]>([])
const tableRef = ref()

const typeMap: Record<string, string> = { annual: '年报', quarterly: '季报', comparison: '对比' }

const genForm = reactive({
  docIds: [] as number[],
  company_code: '',
  fiscal_year: new Date().getFullYear(),
  report_type: 'annual',
})

function resetGenForm() {
  genForm.docIds = []
  genForm.company_code = ''
  genForm.fiscal_year = new Date().getFullYear()
  genForm.report_type = 'annual'
}

function onSelectionChange(rows: any[]) {
  selectedIds.value = rows.map(r => r.id)
}

async function fetchDocs() {
  try {
    const res: any = await getDocumentsApi({ parse_status: 'completed', page_size: 50 })
    if (res.code === 0) availableDocs.value = res.data.items
  } catch { /* ignore */ }
}

async function fetchReports() {
  loading.value = true
  try {
    const res: any = await getReportsApi()
    if (res.code === 0) reports.value = res.data.items
  } finally { loading.value = false }
}

function openGenerateDialog() {
  fetchDocs()
  dialogVisible.value = true
}

async function handleGenerate() {
  generating.value = true
  try {
    const params: any = {
      company_code: genForm.company_code || 'REPORT',
      fiscal_year: genForm.fiscal_year,
      report_type: genForm.report_type,
    }
    if (genForm.docIds.length > 0) {
      params.document_ids = genForm.docIds.join(',')
      // Auto-fill company_code from first selected doc
      if (!genForm.company_code) {
        const firstDoc = availableDocs.value.find(d => d.id === genForm.docIds[0])
        if (firstDoc) params.company_code = firstDoc.company_code || 'REPORT'
      }
    }
    const res: any = await generateReportApi(params)
    if (res.code === 0) {
      ElMessage.success('报告生成成功')
      dialogVisible.value = false
      fetchReports()
    }
  } finally { generating.value = false }
}

async function viewReport(row: any) {
  try {
    const res: any = await getReportDetailApi(row.id)
    if (res.code === 0) {
      previewContent.value = res.data.content_md || ''
      previewReport.value = row
      previewVisible.value = true
    }
  } catch { /* ignore */ }
}

function downloadReport(row: any) {
  const token = localStorage.getItem('token') || ''
  const url = `/api/v1/reports/${row.id}/download`
  // Use fetch to get blob with auth
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(r => r.blob())
    .then(blob => {
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `报告_${row.company_name}_${row.fiscal_year}.pdf`
      a.click()
    })
}

function downloadMarkdown(row: any) {
  getReportDetailApi(row.id).then((res: any) => {
    if (res.code === 0) {
      const blob = new Blob([res.data.content_md || ''], { type: 'text/markdown' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `报告_${row.company_name}_${row.fiscal_year}.md`
      a.click()
      ElMessage.success('Markdown 已导出')
    }
  })
}

async function handleBatchExport() {
  if (selectedIds.value.length === 0) return
  try {
    const token = localStorage.getItem('token') || ''
    const r = await fetch('/api/v1/reports/batch-export', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify(selectedIds.value),
    })
    const blob = await r.blob()
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = '财务分析报告_批量导出.zip'
    a.click()
    ElMessage.success(`已导出 ${selectedIds.value.length} 份报告`)
  } catch { ElMessage.error('导出失败') }
}

async function handleBatchDelete() {
  if (selectedIds.value.length === 0) return
  await ElMessageBox.confirm(`确定删除选中的 ${selectedIds.value.length} 份报告？`, '批量删除', { type: 'warning' })
  for (const id of selectedIds.value) {
    await deleteReportApi(id)
  }
  ElMessage.success('批量删除完成')
  selectedIds.value = []
  fetchReports()
}

async function handleDelete(row: any) {
  await ElMessageBox.confirm('确定删除该报告？', '提示', { type: 'warning' })
  await deleteReportApi(row.id)
  ElMessage.success('已删除')
  fetchReports()
}

function renderPreview(md: string): string {
  if (!md) return ''
  return md
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/^### (.+)$/gm, '<h3 style="color:#409EFF;margin-top:20px;">$1</h3>')
    .replace(/^## (.+)$/gm, '<h2 style="color:#303133;border-bottom:1px solid #eee;padding-bottom:6px;margin-top:24px;">$1</h2>')
    .replace(/^# (.+)$/gm, '<h1 style="color:#1e3c72;border-bottom:2px solid #409EFF;padding-bottom:10px;">$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n\n/g, '</p><p style="line-height:1.8;margin:8px 0;">')
    .replace(/\n/g, '<br/>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/((?:<li>.*?<\/li>\s*)+)/g, '<ul>$1</ul>')
}

onMounted(fetchReports)
</script>
