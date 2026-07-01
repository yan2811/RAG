<!--
  文档列表页面（M1）
  展示用户上传的所有财报文档，支持状态筛选和操作
-->
<template>
  <div class="document-list">
    <!-- 操作栏 -->
    <el-card style="margin-bottom: 16px;">
      <el-row :gutter="16" align="middle">
        <el-col :span="18">
          <el-form :inline="true">
            <el-form-item label="解析状态">
              <el-select v-model="filterStatus" placeholder="全部" clearable @change="fetchDocuments">
                <el-option label="待解析" value="pending" />
                <el-option label="解析中" value="parsing" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-col>
        <el-col :span="6" style="text-align: right;">
          <el-button type="primary" @click="$router.push('/documents/upload')">
            <el-icon><Upload /></el-icon>上传财报 PDF
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 文档表格 -->
    <el-card>
      <el-table :data="tableData" border stripe v-loading="loading" @row-click="goDetail" style="cursor: pointer;">
        <el-table-column prop="id" label="ID" width="50" />
        <el-table-column prop="file_name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="company_code" label="股票代码" width="100" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ docTypeMap[row.doc_type] || row.doc_type || '未分类' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="财年" width="70">
          <template #default="{ row }">{{ row.fiscal_year || '-' }}</template>
        </el-table-column>
        <el-table-column label="解析状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.parse_status)" size="small">
              {{ statusMap[row.parse_status] || row.parse_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="页数" width="60">
          <template #default="{ row }">{{ row.page_count || '-' }}</template>
        </el-table-column>
        <el-table-column label="上传时间" width="170">
          <template #default="{ row }">{{ row.created_at?.substring(0, 16) || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="goDetail(row)">详情</el-button>
            <el-button type="danger" link size="small" @click.stop="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 空状态 -->
      <el-empty v-if="!loading && tableData.length === 0" description="暂无文档，请上传财报 PDF">
        <el-button type="primary" @click="$router.push('/documents/upload')">上传文档</el-button>
      </el-empty>

      <!-- 分页 -->
      <div v-if="pagination.total > 0" style="margin-top: 16px; text-align: right;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchDocuments"
          @current-change="fetchDocuments"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
/**
 * 文档列表页面
 * 展示当前用户上传的所有财报文档
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getDocumentsApi, deleteDocumentApi } from '@/api/document'

const router = useRouter()

/** 状态映射 */
const statusMap: Record<string, string> = {
  pending: '待解析', parsing: '解析中', completed: '已完成', failed: '解析失败',
}
const docTypeMap: Record<string, string> = {
  annual_report: '年报', quarterly_report: '季报', prospectus: '招股书', audit_report: '审计报告', other: '其他',
}

/** 筛选条件 */
const filterStatus = ref('')

/** 分页 */
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

/** 表格数据 */
const tableData = ref<any[]>([])
const loading = ref(false)

/**
 * 获取文档列表
 */
async function fetchDocuments() {
  loading.value = true
  try {
    const res: any = await getDocumentsApi({
      page: pagination.page,
      page_size: pagination.pageSize,
      parse_status: filterStatus.value || undefined,
    })
    if (res.code === 0) {
      tableData.value = res.data.items
      pagination.total = res.data.total
    }
  } finally {
    loading.value = false
  }
}

/** 解析状态对应的 Tag 类型 */
function statusTagType(status: string): string {
  const map: Record<string, string> = { pending: 'info', parsing: 'warning', completed: 'success', failed: 'danger' }
  return map[status] || 'info'
}

/** 跳转文档详情 */
function goDetail(row: any) {
  router.push(`/documents/${row.id}`)
}

/** 删除文档 */
async function handleDelete(row: any) {
  await ElMessageBox.confirm(`确定删除文档「${row.file_name}」吗？`, '删除确认', { type: 'warning' })
  try {
    await deleteDocumentApi(row.id)
    ElMessage.success('文档已删除')
    fetchDocuments()
  } catch { /* error handled in interceptor */ }
}

onMounted(fetchDocuments)
</script>
