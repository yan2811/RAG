<!--
  首页工作台 —— 深蓝科技风
-->
<template>
  <div class="dashboard">
    <h3 class="page-title">系统概览</h3>

    <!-- KPI 统计卡片 -->
    <el-row :gutter="16">
      <el-col :span="6">
        <div class="stat-card" @click="$router.push('/documents')">
          <div class="stat-icon" style="background: rgba(64,158,255,0.12);">
            <el-icon :size="26" color="#409EFF"><Document /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ stats.total_documents }}</div>
            <div class="stat-label">文档总数</div>
            <div class="stat-sub">已解析 {{ stats.completed_documents }} 份</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" @click="$router.push('/knowledge')">
          <div class="stat-icon" style="background: rgba(103,194,58,0.12);">
            <el-icon :size="26" color="#67c23a"><Collection /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ stats.total_chunks || 0 }}</div>
            <div class="stat-label">知识库分块</div>
            <div class="stat-sub">{{ stats.total_vectors || 0 }} 向量</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card" @click="$router.push('/reports')">
          <div class="stat-icon" style="background: rgba(230,162,60,0.12);">
            <el-icon :size="26" color="#e6a23c"><Tickets /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ reportCount }}</div>
            <div class="stat-label">生成报告</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: rgba(168,85,247,0.12);">
            <el-icon :size="26" color="#a855f7"><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-body">
            <div class="stat-value">{{ stats.total_companies }}</div>
            <div class="stat-label">覆盖公司</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 快捷入口 -->
    <el-card class="section-card">
      <template #header><span class="card-title">快捷入口</span></template>
      <el-row :gutter="12">
        <el-col :span="6" v-for="item in quickLinks" :key="item.path">
          <div class="quick-link" @click="$router.push(item.path)">
            <div class="ql-icon" :style="{ background: item.bg }">
              <el-icon :size="22" :color="item.color"><component :is="item.icon" /></el-icon>
            </div>
            <span class="ql-label">{{ item.label }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 最近报告 -->
    <el-card v-if="recentReports.length > 0" class="section-card">
      <template #header><span class="card-title">最近报告</span></template>
      <el-table :data="recentReports" size="small">
        <el-table-column prop="company_name" label="公司" />
        <el-table-column prop="fiscal_year" label="财年" width="80" />
        <el-table-column label="生成时间" width="180">
          <template #default="{ row }">{{ row.created_at?.substring(0, 16) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default>
            <el-button type="primary" link size="small" @click="$router.push('/reports')">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted } from 'vue'
import { getOverviewApi } from '@/api/knowledge'
import { getReportsApi } from '@/api/report'

const stats = reactive({ total_documents: 0, completed_documents: 0, total_companies: 0, total_chunks: 0, total_vectors: 0 })
const reportCount = ref(0)
const recentReports = ref<any[]>([])

const quickLinks = [
  { path: '/documents/upload', icon: 'Upload', color: '#409EFF', bg: 'rgba(64,158,255,0.1)', label: '上传文档' },
  { path: '/chat', icon: 'ChatDotRound', color: '#67c23a', bg: 'rgba(103,194,58,0.1)', label: '智能问答' },
  { path: '/reports', icon: 'Tickets', color: '#e6a23c', bg: 'rgba(230,162,60,0.1)', label: '报告中心' },
  { path: '/knowledge', icon: 'Collection', color: '#a855f7', bg: 'rgba(168,85,247,0.1)', label: '知识库' },
]

onMounted(async () => {
  try { const res: any = await getOverviewApi(); if (res.code === 0) Object.assign(stats, res.data) } catch { /* ignore */ }
  try {
    const res: any = await getReportsApi({ page_size: 5 })
    if (res.code === 0) { reportCount.value = res.data.total || 0; recentReports.value = res.data.items || [] }
  } catch { /* ignore */ }
})
</script>

<style scoped>
.page-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; color: var(--text-primary); }

/* ===== 统计卡片 ===== */
.stat-card {
  cursor: pointer; display: flex; align-items: center; gap: 14px;
  padding: 18px; border-radius: 8px;
  background: rgba(255,255,255,0.03); border: 1px solid rgba(64,158,255,0.06);
  transition: all 0.25s;
  animation: fadeUp 0.5s ease-out both;
}
.stat-card:nth-child(1) { animation-delay: 0.05s; }
.stat-card:nth-child(2) { animation-delay: 0.15s; }
.stat-card:nth-child(3) { animation-delay: 0.25s; }
.stat-card:nth-child(4) { animation-delay: 0.35s; }
.stat-card:hover {
  transform: translateY(-4px);
  border-color: rgba(64,158,255,0.25);
  background: rgba(255,255,255,0.05);
}
.stat-icon {
  width: 50px; height: 50px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.stat-value { font-size: 26px; font-weight: 700; color: #e0e6f0; line-height: 1.1; }
.stat-label { font-size: 13px; color: #8ba4cc; margin-top: 2px; }
.stat-sub { font-size: 11px; color: #5a7a9a; margin-top: 2px; }

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== 区块卡片 ===== */
.section-card { margin-top: 16px; }
.card-title { font-size: 14px; font-weight: 500; color: #8ba4cc; }

/* ===== 快捷入口 ===== */
.quick-link {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 16px 12px; border-radius: 10px; cursor: pointer;
  transition: all 0.2s; border: 1px solid transparent;
}
.quick-link:hover {
  background: rgba(64,158,255,0.05);
  border-color: rgba(64,158,255,0.15);
  transform: translateY(-2px);
}
.ql-icon {
  width: 44px; height: 44px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
}
.ql-label { font-size: 13px; color: #8ba4cc; }
</style>
