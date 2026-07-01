<!--
  财报分析仪表盘（M6）— AI 智能图表版
-->
<template>
  <div class="analytics-dashboard">
    <el-card style="margin-bottom: 16px;">
      <el-select v-model="selectedDocId" placeholder="选择已解析的财报文档" @change="onDocChange" style="width: 420px;">
        <el-option v-for="doc in availableDocs" :key="doc.id"
          :label="`${doc.file_name}（${doc.company_code || '-'} ${doc.fiscal_year || '-'}）`" :value="doc.id" />
      </el-select>
      <el-button type="primary" style="margin-left: 12px;" @click="loadAiCharts(false)" :loading="aiLoading" :disabled="!selectedDocId">
        {{ aiLoading ? 'AI 分析生成中...' : 'AI 智能分析' }}
      </el-button>
      <el-button v-if="!aiLoading && chartData?._cached" @click="loadAiCharts(true)" style="margin-left: 4px;">
        <el-icon><Refresh /></el-icon> 刷新分析
      </el-button>
      <el-tag v-if="!aiLoading && chartData" style="margin-left: 8px;" :type="chartData._cached ? 'success' : 'info'" size="small">
        {{ chartData._cached ? '已缓存' : '最新分析' }}
      </el-tag>
    </el-card>

    <div v-if="!chartData && !data">
      <el-empty description="选择文档后点击「AI 智能分析」生成图表" />
    </div>

    <!-- AI 分析中 -->
    <div v-if="aiLoading" style="text-align: center; padding: 60px;">
      <el-icon class="is-loading" :size="48" color="#409EFF"><Loading /></el-icon>
      <p style="margin-top: 16px; color: #8ba4cc; font-size: 16px;">AI 正在分析财报数据，生成智能图表...</p>
      <p style="color: #5a7a9a; font-size: 13px;">正在提取财务指标、分析数据结构、推荐最佳可视化方案</p>
    </div>

    <template v-if="chartData && !aiLoading">
      <el-alert show-icon :closable="false" style="margin-bottom:16px;">
        <template #title>
          {{ chartData.document_info?.file_name }} · {{ chartData.document_info?.fiscal_year }}年度
          · AI 智能分析结果
        </template>
      </el-alert>

      <!-- 指标卡片 -->
      <el-row :gutter="12" style="margin-bottom: 16px;" v-if="chartData.metrics?.length">
        <el-col :span="4" v-for="m in chartData.metrics.slice(0, 6)" :key="m.name">
          <el-card class="metric-card" shadow="hover">
            <div class="metric-name">{{ m.name }}</div>
            <div class="metric-value">{{ m.value }}{{ m.unit || '' }}</div>
            <div v-if="m.yoy" class="metric-change" :class="m.yoy > 0 ? 'up' : 'down'">
              同比 {{ m.yoy > 0 ? '+' : '' }}{{ m.yoy }}%
            </div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 传统提取的回退指标 -->
      <el-row :gutter="12" style="margin-bottom: 16px;" v-if="!chartData.metrics?.length && data?.base_metrics">
        <el-col :span="4" v-for="m in data.base_metrics.slice(0, 6)" :key="m.name">
          <el-card class="metric-card" shadow="hover">
            <div class="metric-name">{{ m.name }}</div>
            <div class="metric-value">{{ m.value || '-' }}</div>
          </el-card>
        </el-col>
      </el-row>

      <!-- AI 生成的图表 -->
      <el-row :gutter="16">
        <el-col :span="chart.col" v-for="(chart, idx) in displayCharts" :key="idx">
          <el-card style="margin-bottom: 16px;">
            <template #header>
              <span>{{ chart.title || '图表 ' + (idx + 1) }}</span>
              <el-tag size="small" style="margin-left: 8px;">{{ chart.type }}</el-tag>
            </template>
            <div :ref="el => setChartRef(idx, el)" style="height: 340px;"></div>
          </el-card>
        </el-col>
      </el-row>

      <!-- 无图表时显示传统数据 -->
      <template v-if="displayCharts.length === 0 && data">
        <el-empty description="AI 未生成图表，请尝试上传更完整的财报文档" />
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import * as echarts from 'echarts'
import { getDashboardApi, generateAiChartsApi } from '@/api/report'
import { getDocumentsApi } from '@/api/document'

const route = useRoute()

const availableDocs = ref<any[]>([])
const selectedDocId = ref<number | null>(Number(route.params.docId) || null)
const data = ref<any>(null)        // 传统提取数据
const chartData = ref<any>(null)   // AI 生成数据
const aiLoading = ref(false)

const chartRefs: Record<number, any> = {}
const chartInstances: Record<number, echarts.ECharts> = {}

function setChartRef(idx: number, el: any) {
  if (el) chartRefs[idx] = el
}

/** 需要展示的图表 */
const displayCharts = computed(() => {
  const charts = chartData.value?.charts || []
  return charts.map((c: any, i: number) => ({
    ...c,
    col: charts.length === 1 ? 24 : 12,
  }))
})

function onDocChange() {
  if (selectedDocId.value) loadAiCharts(false)
}

async function fetchDocs() {
  try {
    const res: any = await getDocumentsApi({ parse_status: 'completed', page_size: 50 })
    if (res.code === 0) availableDocs.value = res.data.items
  } catch { /* ignore */ }
}

async function loadAiCharts(refresh: boolean = false) {
  if (!selectedDocId.value) return
  aiLoading.value = true
  chartData.value = null
  try {
    const res: any = await generateAiChartsApi(selectedDocId.value, refresh)
    if (res.code === 0) {
      chartData.value = res.data
      await nextTick()
      setTimeout(() => renderAllCharts(), 200)  // wait for DOM
    }
  } finally {
    aiLoading.value = false
  }
}

function renderAllCharts() {
  Object.values(chartInstances).forEach(c => c.dispose())
  Object.keys(chartInstances).forEach(k => delete chartInstances[Number(k)])

  displayCharts.value.forEach((chart: any, idx: number) => {
    const el = chartRefs[idx]
    if (!el) return
    const instance = echarts.init(el)
    chartInstances[idx] = instance

    const opt: any = {
      tooltip: { trigger: chart.type === 'pie' ? 'item' : 'axis' },
    }

    if (chart.type === 'pie') {
      opt.series = [{
        type: 'pie', radius: ['40%', '70%'],
        data: (chart.data?.labels || []).map((l: string, i: number) => ({
          name: l, value: chart.data?.values?.[i] || 0,
        })),
        label: { formatter: '{b}\n{d}%' },
      }]
    } else if (chart.type === 'radar') {
      opt.radar = {
        shape: 'polygon', radius: '65%',
        indicator: (chart.data?.labels || []).map((l: string) => ({ name: l, max: 100 })),
      }
      opt.series = [{ type: 'radar', data: [{ value: chart.data?.values || [], areaStyle: { color: 'rgba(64,158,255,0.2)' } }] }]
    } else if (chart.type === 'bar' || chart.type === 'line') {
      opt.xAxis = { type: 'category', data: chart.data?.labels || [] }
      opt.yAxis = { type: 'value' }
      opt.series = [{
        type: chart.type, data: chart.data?.values || [],
        smooth: chart.type === 'line',
        itemStyle: { color: '#409EFF' },
      }]
    } else {
      // 默认柱状图
      opt.xAxis = { type: 'category', data: chart.data?.labels || [] }
      opt.yAxis = { type: 'value' }
      opt.series = [{ type: 'bar', data: chart.data?.values || [] }]
    }

    instance.setOption(opt)
  })
}

onMounted(async () => {
  await fetchDocs()
  if (selectedDocId.value) loadAiCharts()
})

window.addEventListener('resize', () => {
  Object.values(chartInstances).forEach(c => c.resize())
})
</script>

<style scoped>
.metric-card { text-align: center; }
.metric-name { font-size: 12px; color: #909399; }
.metric-value { font-size: 22px; font-weight: 700; color: #e0e6f0; margin: 4px 0; }
.metric-change { font-size: 12px; }
.metric-change.up { color: #67c23a; }
.metric-change.down { color: #f56c6c; }
</style>
