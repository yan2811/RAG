<!--
  数据可视化大屏 —— 淡蓝 + 金色金融风
-->
<template>
  <div class="big-screen">
    <!-- 返回按钮 -->
    <div class="back-btn" @click="$router.push('/dashboard')">
      <el-icon :size="16"><Close /></el-icon>
    </div>

    <!-- 顶部标题栏 -->
    <div class="screen-top">
      <div class="top-left">
        <div class="top-deco" />
        <span class="top-label">数据监控中心</span>
      </div>
      <h1 class="top-title">财报 RAG 知识库系统</h1>
      <div class="top-right">
        <span class="top-time">{{ now }}</span>
        <span class="top-refresh">· 刷新 {{ refreshCountdown }}s</span>
      </div>
    </div>

    <!-- KPI 卡片行 -->
    <div class="kpi-row">
      <div class="kpi-card" v-for="kpi in kpiCards" :key="kpi.label">
        <div class="kpi-left">
          <div class="kpi-icon" :style="{ background: kpi.gradient }">
            <el-icon :size="20"><component :is="kpi.icon" /></el-icon>
          </div>
        </div>
        <div class="kpi-right">
          <div class="kpi-label">{{ kpi.label }}</div>
          <div class="kpi-value">{{ kpi.value }}</div>
          <div class="kpi-sub">{{ kpi.sub }}</div>
        </div>
      </div>
    </div>

    <!-- 主体三栏 -->
    <div class="screen-body">
      <!-- 左栏 -->
      <div class="col col-left">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">年度文档分布</span>
          </div>
          <div ref="yearChartRef" style="height: 220px;" />
        </div>
        <div class="panel" style="flex: 1;">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">解析状态</span>
          </div>
          <div ref="statusChartRef" style="height: 180px;" />
        </div>
        <div class="panel" style="flex: 1;">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">已覆盖公司 ({{ data.companies?.length || 0 }})</span>
          </div>
          <div class="company-scroll" v-if="data.companies?.length">
            <div v-for="c in data.companies" :key="c.code" class="company-row">
              <span class="comp-code">{{ c.code }}</span>
              <span class="comp-name">{{ (c.name || c.code).substring(0, 12) }}</span>
              <span class="comp-count">{{ c.doc_count }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="30" />
        </div>
      </div>

      <!-- 中栏 -->
      <div class="col col-center">
        <div class="panel hero-panel">
          <div class="hero-number">{{ data.system_status?.total_documents || 0 }}</div>
          <div class="hero-label">知识库文档总数</div>
          <div class="hero-sub">
            <span>已解析 {{ data.system_status?.completed_documents || 0 }}</span>
            <span class="hero-sep">|</span>
            <span>成功率 {{ data.system_status?.parse_success_rate || 0 }}%</span>
            <span class="hero-sep">|</span>
            <span>分块 {{ data.system_status?.total_chunks || 0 }}</span>
          </div>
        </div>
        <div class="panel activity-panel">
          <div class="panel-header">
            <span class="panel-dot dot-live" />
            <span class="panel-title">实时动态</span>
            <span class="live-badge">LIVE</span>
          </div>
          <div class="activity-scroll" v-if="data.recent_activity?.length">
            <div v-for="(act, i) in data.recent_activity" :key="i" class="activity-item">
              <span class="act-time">{{ act.time }}</span>
              <span class="act-tag" :class="act.role === 'user' ? 'tag-ask' : 'tag-reply'">
                {{ act.role === 'user' ? '提问' : 'AI' }}
              </span>
              <span class="act-text">{{ act.content }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无活动" :image-size="30" />
        </div>
      </div>

      <!-- 右栏 -->
      <div class="col col-right">
        <div class="panel">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">高频问题 Top 5</span>
          </div>
          <div class="top-questions" v-if="data.qa_metrics?.top_questions?.length">
            <div v-for="(q, i) in data.qa_metrics.top_questions" :key="i" class="top-q-item">
              <span class="q-rank" :class="'rank-' + (i + 1)">{{ i + 1 }}</span>
              <span class="q-text">{{ q.question }}</span>
              <span class="q-count">{{ q.count }}次</span>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="30" />
        </div>
        <div class="panel">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">问答统计</span>
          </div>
          <div class="stats-grid">
            <div class="stat-cell">
              <div class="stat-val highlight">{{ data.qa_metrics?.today_questions || 0 }}</div>
              <div class="stat-lbl">今日问答</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val">{{ data.qa_metrics?.total_questions || 0 }}</div>
              <div class="stat-lbl">累计问答</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val" :style="{ color: (data.qa_metrics?.satisfaction_rate || 0) >= 80 ? '#2d8c5a' : '#c8993d' }">
                {{ data.qa_metrics?.satisfaction_rate || 0 }}%
              </div>
              <div class="stat-lbl">满意度</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val">{{ data.system_status?.total_reports || 0 }}</div>
              <div class="stat-lbl">生成报告</div>
            </div>
          </div>
        </div>
        <div class="panel" style="flex: 1;">
          <div class="panel-header">
            <span class="panel-dot" />
            <span class="panel-title">最近报告</span>
          </div>
          <div v-if="data.recent_reports?.length" class="report-list">
            <div v-for="r in data.recent_reports" :key="r.id" class="report-item">
              <el-icon :size="14" color="#1a3c6e"><Document /></el-icon>
              <span class="rpt-name">{{ r.company_name || '-' }}</span>
              <span class="rpt-year">{{ r.fiscal_year }}</span>
            </div>
          </div>
          <el-empty v-else description="暂无数据" :image-size="30" />
        </div>
      </div>
    </div>

    <!-- 底部 -->
    <div class="screen-bottom">
      <span>DeepSeek-V4-Pro</span><span class="bot-sep">|</span>
      <span>ChromaDB 向量检索</span><span class="bot-sep">|</span>
      <span>BGE Embedding</span><span class="bot-sep">|</span>
      <span>PyMuPDF 解析</span><span class="bot-sep">|</span>
      <span>系统运行正常</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '@/utils/request'

const now = ref('')
const refreshCountdown = ref(60)
let clockTimer: any = null, refreshTimer: any = null, cdTimer: any = null
const yearChartRef = ref(null), statusChartRef = ref(null)
let yearChart: any = null, statusChart: any = null

const data = reactive<any>({
  system_status: {}, qa_metrics: { top_questions: [] },
  companies: [], year_distribution: [], recent_activity: [], recent_reports: [],
})

const kpiCards = computed(() => [
  { label: '知识库文档', value: data.system_status?.total_documents || 0, sub: `已解析 ${data.system_status?.completed_documents || 0} 份`, icon: 'Document', gradient: 'linear-gradient(135deg, #1a3c6e, #254d8a)' },
  { label: '累计问答量', value: data.qa_metrics?.total_questions || 0, sub: `今日 ${data.qa_metrics?.today_questions || 0} 次`, icon: 'ChatDotRound', gradient: 'linear-gradient(135deg, #2d8c5a, #3baa6e)' },
  { label: '用户满意度', value: (data.qa_metrics?.satisfaction_rate || 0) + '%', sub: `${data.qa_metrics?.total_feedback || 0} 条反馈`, icon: 'Star', gradient: 'linear-gradient(135deg, #c8993d, #d4a542)' },
  { label: '覆盖公司', value: data.system_status?.total_companies || 0, sub: `${data.system_status?.total_chunks || 0} 个分块`, icon: 'OfficeBuilding', gradient: 'linear-gradient(135deg, #546e7a, #455a64)' },
])

async function fetchData() {
  try {
    const res: any = await request.get('/dashboard/bigscreen')
    if (res.code === 0 && res.data) { Object.assign(data, res.data); await nextTick(); renderCharts() }
  } catch { /* ignore */ }
}

function updateTime() {
  const d = new Date()
  now.value = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0') + ' ' +
    String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0') + ':' + String(d.getSeconds()).padStart(2,'0')
}

function renderCharts() { renderYearChart(); renderStatusChart() }

function renderYearChart() {
  if (!yearChartRef.value) return
  if (yearChart) yearChart.dispose()
  yearChart = echarts.init(yearChartRef.value)
  const years = data.year_distribution?.map((y: any) => y.year + '年') || []
  const counts = data.year_distribution?.map((y: any) => y.count) || []
  yearChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { top: 15, bottom: 20, left: 35, right: 10 },
    xAxis: { type: 'category', data: years, axisLabel: { color: '#54677a', fontSize: 10 }, axisLine: { lineStyle: { color: '#d0d7e0' } } },
    yAxis: { type: 'value', axisLabel: { color: '#54677a', fontSize: 10 }, splitLine: { lineStyle: { color: '#e8ecf1' } } },
    series: [{ type: 'bar', data: counts, barWidth: '45%', itemStyle: { borderRadius: [4,4,0,0], color: new echarts.graphic.LinearGradient(0,0,0,1, [{ offset: 0, color: '#3b6fc2' }, { offset: 1, color: '#1a3c6e' }]) } }],
  })
}

function renderStatusChart() {
  if (!statusChartRef.value) return
  if (statusChart) statusChart.dispose()
  statusChart = echarts.init(statusChartRef.value)
  const completed = data.system_status?.completed_documents || 0
  const failed = data.system_status?.failed_documents || 0
  const pending = (data.system_status?.total_documents || 0) - completed - failed
  statusChart.setOption({
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#54677a', fontSize: 10 }, itemWidth: 8, itemHeight: 8 },
    series: [{ type: 'pie', radius: ['55%','78%'], center: ['50%','45%'], label: { show: false }, emphasis: { label: { show: true, fontSize: 14 } },
      data: [
        { value: completed, name: '已解析', itemStyle: { color: '#2d8c5a' } },
        { value: pending, name: '待解析', itemStyle: { color: '#c8993d' } },
        { value: failed, name: '失败', itemStyle: { color: '#b8453a' } },
      ] }],
  })
}

onMounted(() => {
  updateTime(); clockTimer = setInterval(updateTime, 1000); fetchData()
  refreshTimer = setInterval(() => { fetchData(); refreshCountdown.value = 60 }, 60000)
  cdTimer = setInterval(() => { if (refreshCountdown.value > 0) refreshCountdown.value-- }, 1000)
})
onUnmounted(() => { clearInterval(clockTimer); clearInterval(refreshTimer); clearInterval(cdTimer); yearChart?.dispose(); statusChart?.dispose() })
</script>

<style scoped>
/* ===== 全屏容器 ===== */
.big-screen {
  position: fixed; inset: 0; z-index: 999;
  background: linear-gradient(160deg, #e8f0f8 0%, #dce6f2 30%, #eaf1f9 60%, #d5e1f0 100%);
  color: #1e2b3c; font-family: 'Microsoft YaHei','PingFang SC',sans-serif;
  display: flex; flex-direction: column; padding: 10px 24px 8px; overflow-y: auto;
}

/* 返回按钮 - 左上角 */
.back-btn {
  position: fixed; top: 10px; left: 24px; z-index: 1001;
  width: 32px; height: 32px; border-radius: 6px;
  background: rgba(26,60,110,0.06); display: flex; align-items: center; justify-content: center;
  cursor: pointer; color: #54677a; border: 1px solid rgba(26,60,110,0.1);
  transition: all 0.2s;
}
.back-btn:hover { background: rgba(26,60,110,0.12); color: #1a3c6e; border-color: #1a3c6e; }

/* ===== 顶部 ===== */
.screen-top {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 0 8px; border-bottom: 1px solid rgba(26,60,110,0.1); margin-bottom: 10px;
}
.top-left { display: flex; align-items: center; gap: 8px; }
.top-deco { width: 3px; height: 14px; background: linear-gradient(180deg, #c8a951, #1a3c6e); border-radius: 2px; }
.top-label { font-size: 12px; color: #54677a; letter-spacing: 2px; }
.top-title { font-size: 20px; font-weight: 700; color: #1a3c6e; letter-spacing: 2px; margin: 0; }
.top-right { display: flex; align-items: center; gap: 8px; font-size: 12px; color: #8b9aab; }

/* ===== KPI 卡片 ===== */
.kpi-row { display: flex; gap: 12px; margin-bottom: 10px; }
.kpi-card {
  flex: 1; display: flex; align-items: center; gap: 12px;
  padding: 14px 16px; background: #fff; border-radius: 8px;
  border: 1px solid rgba(26,60,110,0.06);
  box-shadow: 0 2px 8px rgba(26,60,110,0.04);
  transition: box-shadow 0.3s, transform 0.3s;
}
.kpi-card:hover { box-shadow: 0 4px 16px rgba(26,60,110,0.08); transform: translateY(-1px); }
.kpi-icon {
  width: 42px; height: 42px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: #fff;
}
.kpi-label { font-size: 11px; color: #8b9aab; }
.kpi-value { font-size: 24px; font-weight: 700; color: #1e2b3c; line-height: 1.2; }
.kpi-sub { font-size: 11px; color: #8b9aab; margin-top: 2px; }

/* ===== 三栏 ===== */
.screen-body { flex: 1; display: flex; gap: 12px; min-height: 0; }
.col { display: flex; flex-direction: column; gap: 10px; }
.col-left { width: 280px; }
.col-center { flex: 1; }
.col-right { width: 290px; }

/* ===== 面板 ===== */
.panel {
  background: #fff; border-radius: 8px;
  border: 1px solid rgba(26,60,110,0.06);
  box-shadow: 0 2px 8px rgba(26,60,110,0.03);
  padding: 12px;
}
.panel-header { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; }
.panel-dot { width: 6px; height: 6px; border-radius: 50%; background: #1a3c6e; }
.dot-live { background: #2d8c5a; animation: pulse 1.5s infinite; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
.panel-title { font-size: 12px; color: #54677a; font-weight: 500; }
.live-badge { margin-left: auto; font-size: 10px; color: #2d8c5a; letter-spacing: 1px; padding: 1px 6px; border: 1px solid rgba(45,140,90,0.3); border-radius: 2px; }

/* 英雄数字 */
.hero-panel { text-align: center; padding: 24px 12px 16px; }
.hero-number { font-size: 72px; font-weight: 800; color: #c8a951; line-height: 1; }
.hero-label { font-size: 15px; color: #54677a; margin-top: 8px; letter-spacing: 4px; }
.hero-sub { font-size: 12px; color: #8b9aab; margin-top: 8px; }
.hero-sep { margin: 0 8px; color: #d0d7e0; }

/* 实时动态 */
.activity-panel { flex: 1; display: flex; flex-direction: column; }
.activity-scroll { flex: 1; overflow-y: auto; max-height: 260px; }
.activity-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f2f5; font-size: 11px; }
.act-time { color: #8b9aab; min-width: 42px; }
.act-tag { font-size: 10px; padding: 1px 5px; border-radius: 2px; }
.tag-ask { color: #1a3c6e; background: rgba(26,60,110,0.06); }
.tag-reply { color: #2d8c5a; background: rgba(45,140,90,0.06); }
.act-text { color: #54677a; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 公司列表 */
.company-scroll { max-height: 180px; overflow-y: auto; }
.company-row { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-bottom: 1px solid #f5f6f8; font-size: 12px; }
.comp-code { color: #1a3c6e; font-weight: 600; min-width: 56px; }
.comp-name { color: #1e2b3c; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.comp-count { color: #8b9aab; }

/* 高频问题 */
.top-questions { display: flex; flex-direction: column; gap: 5px; }
.top-q-item { display: flex; align-items: center; gap: 8px; font-size: 12px; }
.q-rank { width: 18px; height: 18px; border-radius: 4px; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; background: #8b9aab; }
.rank-1 { background: #b8453a; } .rank-2 { background: #c8993d; } .rank-3 { background: #1a3c6e; }
.q-text { flex: 1; color: #1e2b3c; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.q-count { color: #8b9aab; font-size: 11px; }

/* 统计网格 */
.stats-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.stat-cell { text-align: center; padding: 10px 6px; background: #f6f8fb; border-radius: 6px; }
.stat-val { font-size: 20px; font-weight: 700; color: #1e2b3c; }
.stat-val.highlight { color: #1a3c6e; }
.stat-lbl { font-size: 10px; color: #8b9aab; margin-top: 2px; }

/* 报告 */
.report-list { display: flex; flex-direction: column; gap: 4px; }
.report-item { display: flex; align-items: center; gap: 6px; padding: 4px 0; font-size: 11px; color: #54677a; }
.rpt-name { flex: 1; } .rpt-year { color: #8b9aab; }

/* 底部 */
.screen-bottom { text-align: center; padding-top: 6px; margin-top: 6px; border-top: 1px solid rgba(26,60,110,0.06); font-size: 10px; color: #8b9aab; }
.bot-sep { margin: 0 12px; color: #d0d7e0; }

/* 滚动条 */
.activity-scroll::-webkit-scrollbar, .company-scroll::-webkit-scrollbar { width: 3px; }
.activity-scroll::-webkit-scrollbar-thumb, .company-scroll::-webkit-scrollbar-thumb { background: rgba(26,60,110,0.1); border-radius: 2px; }
</style>
