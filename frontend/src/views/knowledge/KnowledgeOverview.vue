<!--
  知识库管理 —— 分块表格 + AI自动标签
-->
<template>
  <div class="knowledge-page">
    <!-- 统计卡片 -->
    <el-row :gutter="12" style="margin-bottom: 12px;">
      <el-col :span="4" v-for="s in statCards" :key="s.label">
        <el-card class="mini-stat" shadow="hover">
          <div class="mini-num">{{ s.value }}</div><div class="mini-label">{{ s.label }}</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 文档筛选 + 分块表格 -->
    <el-card>
      <template #header>
        <el-row justify="space-between" align="middle">
          <span>知识库分块列表</span>
          <div>
            <el-select v-model="filterDocId" placeholder="按文档筛选" clearable style="width: 260px;" @change="fetchData">
              <el-option v-for="d in documents" :key="d.id" :label="d.file_name" :value="d.id" />
            </el-select>
            <el-input v-model="searchKw" placeholder="搜索分块内容" clearable style="width: 200px; margin-left: 8px;" @input="onSearch" />
            <el-button type="primary" style="margin-left: 8px;" @click="$router.push('/documents/upload')">上传文档</el-button>
          </div>
        </el-row>
      </template>

      <el-table :data="displayChunks" border stripe v-loading="loading" max-height="550" size="small"
        highlight-current-row @row-click="showDetail">
        <el-table-column prop="doc_name" label="所属文档" width="180" show-overflow-tooltip />
        <el-table-column prop="section_title" label="章节" width="160" show-overflow-tooltip />
        <el-table-column label="类型" width="60">
          <template #default="{ row }">
            <el-tag :type="row.chunk_type === 'table' ? 'warning' : ''" size="small">{{ row.chunk_type === 'table' ? '表格' : '文本' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="200">
          <template #default="{ row }">
            <el-tag v-for="t in (row.tags || [])" :key="t" size="small" style="margin: 1px 2px;" effect="plain">{{ t }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="content_preview" label="内容预览" min-width="280" show-overflow-tooltip />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click.stop="showDetail(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 内容查看弹窗 -->
    <el-dialog v-model="detailVisible" title="分块详情" width="700px" top="5vh">
      <el-descriptions :column="2" size="small" border style="margin-bottom: 12px;">
        <el-descriptions-item label="文档">{{ selectedChunk?.doc_name }}</el-descriptions-item>
        <el-descriptions-item label="章节">{{ selectedChunk?.section_title }}</el-descriptions-item>
        <el-descriptions-item label="类型">{{ selectedChunk?.chunk_type }}</el-descriptions-item>
        <el-descriptions-item label="标签">
          <el-tag v-for="t in (selectedChunk?.tags || [])" :key="t" size="small" style="margin: 1px 2px;">{{ t }}</el-tag>
        </el-descriptions-item>
      </el-descriptions>
      <div style="max-height: 50vh; overflow-y: auto; white-space: pre-wrap; line-height: 1.8; padding: 12px; background: #fafafa; border-radius: 4px;">
        {{ selectedChunk?.content_full }}
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { getDocumentsApi } from '@/api/document'
import { getTagsApi } from '@/api/knowledge'
import request from '@/utils/request'

const loading = ref(false)
const documents = ref<any[]>([])
const allChunks = ref<any[]>([])
const filterDocId = ref<number | null>(null)
const searchKw = ref('')
const detailVisible = ref(false)
const selectedChunk = ref<any>(null)

const statCards = computed(() => [
  { label: '文档总数', value: documents.value.length },
  { label: '分块总数', value: allChunks.value.length },
  { label: '已选中文档', value: filterDocId.value ? 1 : documents.value.filter(d => d.parse_status === 'completed').length },
  { label: '搜索结果', value: displayChunks.value.length },
  { label: '标签数', value: new Set(allChunks.value.flatMap(c => c.tags || [])).size },
  { label: '覆盖公司', value: new Set(documents.value.map(d => d.company_code).filter(Boolean)).size },
])

const displayChunks = computed(() => {
  return allChunks.value.filter(c => {
    if (filterDocId.value && c.document_id !== filterDocId.value) return false
    if (searchKw.value) return c.content_preview?.includes(searchKw.value) || c.section_title?.includes(searchKw.value)
    return true
  })
})

function onSearch() { /* computed handles it */ }

async function fetchData() {
  loading.value = true
  try {
    // Load documents
    const docsRes: any = await getDocumentsApi({ page_size: 200 })
    if (docsRes.code === 0) documents.value = docsRes.data.items

    // Load all chunks for each completed document
    const tagsRes: any = await getTagsApi()
    const tagMap: Record<number, string[]> = {}
    if (tagsRes.code === 0) {
      for (const t of tagsRes.data) {
        // We'll match tags to chunks later
      }
    }

    const chunks: any[] = []
    for (const doc of documents.value) {
      if (doc.parse_status !== 'completed') continue
      try {
        const detailRes: any = await request.get(`/documents/${doc.id}`)
        if (detailRes.code === 0 && detailRes.data?.chunks) {
          for (const c of detailRes.data.chunks) {
            // Find tags for this document
            const docTags = tagsRes.data?.filter((t: any) =>
              t.document_count > 0 && doc.file_name?.includes(t.name)
            ).map((t: any) => t.name) || []
            chunks.push({
              ...c,
              document_id: doc.id,
              doc_name: doc.file_name,
              company_code: doc.company_code,
              tags: docTags.length > 0 ? docTags : (doc.tags || []),
            })
          }
        }
      } catch { /* skip */ }
    }
    allChunks.value = chunks
  } finally { loading.value = false }
}

function showDetail(row: any) {
  selectedChunk.value = row
  detailVisible.value = true
}

onMounted(fetchData)
</script>

<style scoped>
.mini-stat { text-align: center; cursor: default; }
.mini-num { font-size: 24px; font-weight: 700; color: #1a3c6e; }
.mini-label { font-size: 12px; color: #909399; margin-top: 4px; }
</style>
