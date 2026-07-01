<!--
  操作日志页面（M9）
  查询和筛选系统操作日志
-->
<template>
  <div class="operation-logs">
    <el-card>
      <el-form :inline="true" :model="queryForm">
        <el-form-item label="操作类型">
          <el-select v-model="queryForm.action" placeholder="全部" clearable style="width: 160px;">
            <el-option label="登录" value="login" />
            <el-option label="上传" value="upload" />
            <el-option label="删除" value="delete" />
            <el-option label="导出" value="export" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchLogs">查询</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="logs" border stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="操作人" width="120" />
        <el-table-column prop="action" label="操作类型" width="100" />
        <el-table-column prop="target_type" label="操作对象" width="120" />
        <el-table-column prop="ip_address" label="IP 地址" width="140" />
        <el-table-column label="结果" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="操作时间" width="180" />
        <el-table-column label="详情" min-width="200">
          <template #default="{ row }">
            <span v-if="row.detail">{{ JSON.stringify(row.detail) }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 16px; text-align: right;">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          layout="total, prev, pager, next"
          @current-change="fetchLogs"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getLogsApi } from '@/api/admin'

const queryForm = reactive({ action: '' })
const pagination = reactive({ page: 1, pageSize: 30, total: 0 })
const logs = ref<any[]>([])
const loading = ref(false)

async function fetchLogs() {
  loading.value = true
  try {
    const res: any = await getLogsApi({
      page: pagination.page,
      page_size: pagination.pageSize,
      action: queryForm.action || undefined,
    })
    if (res.code === 0) {
      logs.value = res.data.items
      pagination.total = res.data.total
    }
  } finally { loading.value = false }
}

onMounted(fetchLogs)
</script>
