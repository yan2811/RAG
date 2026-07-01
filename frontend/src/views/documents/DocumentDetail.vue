<!--
  文档详情页面（M1）
  元数据 + 分块预览 + 全文查看
-->
<template>
  <div class="document-detail">
    <el-page-header @back="$router.push('/documents')" title="返回文档列表" style="margin-bottom: 16px;">
      <template #content><span>文档详情</span></template>
    </el-page-header>

    <el-skeleton :rows="8" animated v-if="loading" />
    <template v-else-if="doc">
      <!-- 基本信息 -->
      <el-card style="margin-bottom: 16px;">
        <template #header><span>文档信息</span></template>
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="文件名" :span="2">{{ doc.file_name }}</el-descriptions-item>
          <el-descriptions-item label="文件大小">{{ formatFileSize(doc.file_size) }}</el-descriptions-item>
          <el-descriptions-item label="股票代码">{{ doc.company_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="财年">{{ doc.fiscal_year || '-' }}</el-descriptions-item>
          <el-descriptions-item label="季度">{{ doc.fiscal_quarter === 4 ? '年报' : 'Q' + doc.fiscal_quarter }}</el-descriptions-item>
          <el-descriptions-item label="解析状态">
            <el-tag :type="statusTagType(doc.parse_status)" size="small">
              {{ statusMap[doc.parse_status] || doc.parse_status }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="总页数">{{ doc.page_count || '-' }}</el-descriptions-item>
          <el-descriptions-item label="分块数量">{{ doc.chunk_count }}</el-descriptions-item>
          <el-descriptions-item label="上传时间">{{ doc.created_at?.substring(0, 19) || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div style="margin-top: 12px;">
          <el-button type="success" @click="openOriginalFile">
            <el-icon><View /></el-icon>打开原始 PDF
          </el-button>
          <el-button type="primary" @click="handleReparse" :loading="reparsing">
            <el-icon><MagicStick /></el-icon>AI 智能分节 {{ reparsing ? '分析中...' : '' }}
          </el-button>
          <el-button @click="$router.push('/analytics/' + doc.id)">查看仪表盘</el-button>
        </div>
        <el-alert type="info" :closable="false" style="margin-top: 12px;" show-icon>
          <template #title>
            财报文档通常包含复杂表格和排版，建议使用"打开原始 PDF"查看完整内容。系统的文本解析主要用于 AI 检索和分析。
          </template>
        </el-alert>
      </el-card>

      <!-- 分块列表（用于AI检索的文本片段） -->
      <el-card v-if="doc.chunks?.length">
        <template #header><span>文档分块列表（共 {{ doc.chunks.length }} 块）</span></template>
        <el-table :data="doc.chunks" border stripe max-height="400" size="small"
          @row-click="showChunkContent" highlight-current-row style="cursor: pointer;">
          <el-table-column prop="chunk_index" label="序号" width="55" />
          <el-table-column prop="section_title" label="章节" width="150" />
          <el-table-column label="类型" width="60">
            <template #default="{ row }">
              <el-tag :type="row.chunk_type === 'table' ? 'warning' : 'info'" size="small">
                {{ row.chunk_type === 'table' ? '表格' : '文本' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="page_start" label="页码" width="55" />
          <el-table-column prop="content_preview" label="内容预览（点击查看完整内容）" min-width="300" show-overflow-tooltip />
        </el-table>

        <!-- 分块内容查看对话框 -->
        <el-dialog v-model="chunkDialogVisible" :title="'分块 #' + selectedChunk?.chunk_index + ' · ' + selectedChunk?.section_title" width="760px" top="5vh">
          <div style="max-height: 65vh; overflow-y: auto; white-space: pre-wrap; line-height: 1.9; font-size: 14px; padding: 16px; background: #fafafa; border-radius: 4px;">
            {{ selectedChunk?.content_full || selectedChunk?.content_preview }}
          </div>
          <template #footer>
            <el-button @click="chunkDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="copyChunkContent">复制内容</el-button>
          </template>
        </el-dialog>
      </el-card>
    </template>
    <el-empty v-else description="文档不存在或无权访问" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getDocumentDetailApi, triggerParseApi } from '@/api/document'

const route = useRoute()

const doc = ref<any>(null)
const loading = ref(true)
const reparsing = ref(false)

const chunkDialogVisible = ref(false)
const selectedChunk = ref<any>(null)

function showChunkContent(row: any) { selectedChunk.value = row; chunkDialogVisible.value = true }

function copyChunkContent() {
  const text = selectedChunk.value?.content_full || selectedChunk.value?.content_preview || ''
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

const statusMap: Record<string, string> = { pending: '待解析', parsing: '解析中', completed: '已完成', failed: '解析失败' }

function statusTagType(s: string): string {
  const m: Record<string, string> = { pending: 'info', parsing: 'warning', completed: 'success', failed: 'danger' }
  return m[s] || 'info'
}

function formatFileSize(b: number): string {
  if (!b) return '-'
  if (b < 1024) return b + ' B'
  if (b < 1048576) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1048576).toFixed(1) + ' MB'
}

async function fetchDetail() {
  loading.value = true
  try {
    const res: any = await getDocumentDetailApi(Number(route.params.id))
    if (res.code === 0) doc.value = res.data
  } finally { loading.value = false }
}

function openOriginalFile() {
  const token = localStorage.getItem('token') || ''
  window.open(`/api/v1/documents/${doc.value.id}/file?token=${token}`, '_blank')
}

async function handleReparse() {
  reparsing.value = true
  try {
    const res: any = await triggerParseApi(Number(route.params.id))
    if (res.code === 0) { ElMessage.success(res.msg || '分节完成'); fetchDetail() }
    else ElMessage.warning(res.msg || '分节失败')
  } finally { reparsing.value = false }
}

onMounted(fetchDetail)
</script>

<style scoped>
.document-content { max-height: 600px; overflow-y: auto; padding: 16px; background: #fafafa; border-radius: 4px; }
.content-section { margin-bottom: 24px; }
.section-title { font-size: 16px; color: #303133; margin-bottom: 8px; display: flex; align-items: center; gap: 8px; }
.section-text { font-size: 14px; line-height: 2; color: #606266; white-space: pre-wrap; }
</style>
