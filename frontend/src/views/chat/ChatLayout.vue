<!--
  智能问答页面（M4 核心 + M8 对话管理）
  左侧会话列表 + 右侧 SSE 流式对话区
-->
<template>
  <div class="chat-container">
    <!-- 左侧会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" size="small" @click="handleNewSession" style="width: 100%;">
          <el-icon><Plus /></el-icon>新对话
        </el-button>
      </div>
      <div class="session-list">
        <div
          v-for="s in sessions"
          :key="s.id"
          :class="['session-item', { active: s.id === currentSessionId }]"
          @click="switchSession(s.id)"
        >
          <div class="session-title">{{ s.session_title }}</div>
          <div class="session-actions">
            <el-button link size="small" @click.stop="handleDeleteSession(s)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
        <el-empty v-if="sessions.length === 0" description="暂无对话" :image-size="40" />
      </div>
    </div>

    <!-- 右侧对话区 -->
    <div class="chat-main">
      <!-- 消息列表 -->
      <div class="message-list" ref="messageListRef">
        <el-empty v-if="messages.length === 0 && !streaming" description="开始提问吧" :image-size="60" style="margin-top: 80px;" />

        <div v-for="msg in messages" :key="msg.id || 'streaming'" :class="['message-item', msg.role]">
          <div class="message-avatar">
            <el-avatar :size="36" v-if="msg.role === 'user'">
              {{ currentUser?.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <el-avatar :size="36" v-else style="background: #409EFF;">
              <el-icon><ChatDotRound /></el-icon>
            </el-avatar>
          </div>
          <div class="message-body">
            <div class="message-content">
              <div v-if="msg.role === 'assistant'" v-html="renderMarkdown(msg.content)" class="markdown-body"></div>
              <div v-else>{{ msg.content }}</div>
            </div>
            <!-- 来源标注 -->
            <div v-if="msg.sources && msg.sources.length > 0" class="message-sources">
              <span style="color: #909399; font-size: 12px;">数据来源：</span>
              <el-tag
                v-for="(src, i) in msg.sources"
                :key="i"
                size="small"
                effect="plain"
                style="margin: 2px 4px;"
              >
                {{ src.section }} · 第{{ src.page }}页
              </el-tag>
            </div>
            <!-- 反馈按钮 -->
            <div v-if="msg.role === 'assistant' && msg.id" class="message-actions">
              <el-button
                link
                size="small"
                :type="msg.feedback === 'up' ? 'primary' : ''"
                @click="handleFeedback(msg, 'up')"
              >
                <el-icon><CaretTop /></el-icon>
              </el-button>
              <el-button
                link
                size="small"
                :type="msg.feedback === 'down' ? 'danger' : ''"
                @click="handleFeedback(msg, 'down')"
              >
                <el-icon><CaretBottom /></el-icon>
              </el-button>
            </div>
          </div>
        </div>

        <!-- AI 思考中 -->
        <div v-if="streaming && !streamingText" class="message-item assistant">
          <div class="message-avatar">
            <el-avatar :size="36" style="background: #409EFF;">
              <el-icon><ChatDotRound /></el-icon>
            </el-avatar>
          </div>
          <div class="message-body">
            <div class="message-content" style="color: #909399;">
              <el-icon class="is-loading"><Loading /></el-icon>
              AI 正在分析您的问题，检索相关财报内容...
            </div>
          </div>
        </div>

        <!-- 流式输出中的消息 -->
        <div v-if="streaming && streamingText" class="message-item assistant">
          <div class="message-avatar">
            <el-avatar :size="36" style="background: #409EFF;">
              <el-icon><ChatDotRound /></el-icon>
            </el-avatar>
          </div>
          <div class="message-body">
            <div class="message-content" v-html="renderMarkdown(streamingText + '▌')"></div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div class="message-input">
        <div style="display: flex; gap: 8px; margin-bottom: 8px; align-items: center;">
          <el-button size="small" @click="handleAgentAnalyze" :disabled="!inputText.trim() || streaming" style="margin-right: 8px;">
            <el-icon><MagicStick /></el-icon>Agent分析
          </el-button>
          <span style="font-size: 12px; color: #909399; white-space: nowrap;">
            知识库：
            <el-tag :type="chatMode === 'rag' ? 'success' : 'info'" size="small" style="margin-left: 4px;">
              {{ chatMode === 'rag' ? 'RAG检索增强' : 'AI直接回答' }}
            </el-tag>
          </span>
          <el-select
            v-model="selectedDocIds"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="不选则使用AI直接回答"
            size="small"
            style="flex: 1;"
            clearable
            @change="onDocSelectionChange"
          >
            <el-option
              v-for="doc in availableDocs"
              :key="doc.id"
              :label="doc.file_name"
              :value="doc.id"
            />
          </el-select>
        </div>
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入问题，例如：比亚迪2024年毛利率是多少？同比变化如何？"
          :disabled="streaming || !currentSessionId"
          @keydown.enter.exact="handleSend"
          resize="none"
        />
        <el-button
          type="primary"
          :disabled="!inputText.trim() || streaming || !currentSessionId"
          :loading="streaming"
          @click="handleSend"
          style="margin-top: 8px;"
        >
          {{ streaming ? '思考中...' : '发送' }}
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 智能问答页面
 * 左右分栏：会话列表 + 对话区（SSE 流式渲染）
 */
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/user'
import {
  getSessionsApi, createSessionApi, deleteSessionApi,
  getMessagesApi, sendMessageSSE, submitFeedbackApi,
} from '@/api/chat'
import { getDocumentsApi } from '@/api/document'
import { agentAnalyzeApi } from '@/api/report'

const userStore = useUserStore()
const currentUser = computed(() => userStore.user)

/** 会话 */
const sessions = ref<any[]>([])
const currentSessionId = ref<number | null>(null)

/** 消息 */
const messages = ref<any[]>([])
const streaming = ref(false)
const streamingText = ref('')
const thinkingText = ref('')
const messageListRef = ref<HTMLElement>()

/** 文档选择 */
const availableDocs = ref<any[]>([])
const selectedDocIds = ref<number[]>([])
const chatMode = ref<'rag' | 'ai'>('ai')  // 当前模式：rag=知识库检索, ai=直接回答

/** 输入 */
const inputText = ref('')

function onDocSelectionChange(val: number[]) {
  chatMode.value = val.length > 0 ? 'rag' : 'ai'
}

/** 获取可用文档列表 */
async function fetchDocs() {
  try {
    const res: any = await getDocumentsApi({ parse_status: 'completed', page_size: 50 })
    if (res.code === 0) availableDocs.value = res.data.items
  } catch { /* ignore */ }
}

/**
 * 获取会话列表
 */
async function fetchSessions() {
  try {
    const res: any = await getSessionsApi()
    if (res.code === 0) sessions.value = res.data.items
  } catch { /* ignore */ }
}

/**
 * 创建新会话
 */
async function handleNewSession() {
  try {
    const res: any = await createSessionApi()
    if (res.code === 0) {
      currentSessionId.value = res.data.id
      messages.value = []
      fetchSessions()
    }
  } catch { /* ignore */ }
}

/**
 * 切换会话
 */
async function switchSession(sessionId: number) {
  currentSessionId.value = sessionId
  streamingText.value = ''
  try {
    const res: any = await getMessagesApi(sessionId)
    if (res.code === 0) messages.value = res.data.items
  } catch { /* ignore */ }
}

/**
 * 删除会话
 */
async function handleDeleteSession(session: any) {
  try {
    await ElMessageBox.confirm(`确定删除会话「${session.session_title}」吗？`, '提示', { type: 'warning' })
    await deleteSessionApi(session.id)
    if (currentSessionId.value === session.id) {
      currentSessionId.value = null
      messages.value = []
    }
    fetchSessions()
  } catch { /* ignore */ }
}

/**
 * 发送消息
 */
async function handleSend() {
  const question = inputText.value.trim()
  if (!question || !currentSessionId.value || streaming.value) return

  // 添加用户消息到列表
  messages.value.push({ role: 'user', content: question, id: Date.now() })
  inputText.value = ''
  scrollToBottom()

  // 添加占位助手消息
  const assistantMsg: any = { role: 'assistant', content: '', sources: [], id: null, feedback: null }
  messages.value.push(assistantMsg)
  const msgIndex = messages.value.length - 1

  streaming.value = true
  streamingText.value = ''

  sendMessageSSE(
    currentSessionId.value,
    question,
    selectedDocIds.value.length > 0 ? selectedDocIds.value : undefined,
    // onSource (now receives {type:'mode', mode, info, sources})
    (data) => {
      if (data.mode) chatMode.value = data.mode
      assistantMsg.sources = data.sources || []
    },
    // onAnswer
    (chunk) => {
      streamingText.value += chunk
      assistantMsg.content = streamingText.value
    },
    // onDone
    (messageId) => {
      assistantMsg.id = messageId
      streaming.value = false
      streamingText.value = ''
      scrollToBottom()
    },
    // onError
    (err) => {
      assistantMsg.content = err
      streaming.value = false
      streamingText.value = ''
    },
  )
}

/**
 * 简单的 Markdown 渲染（处理代码块、粗体、表格）
 */
function renderMarkdown(text: string): string {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')

  // 代码块
  html = html.replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
  // 行内代码
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>')
  // 粗体
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
  // 表格
  html = html.replace(/\|(.+)\|/g, (match) => {
    const cells = match.split('|').filter(c => c.trim() && !/^[-:\s]+$/.test(c.trim()))
    if (cells.length === 0) return match
    return '<tr>' + cells.map(c => {
      const trimmed = c.trim()
      return trimmed.startsWith('--') ? '' : `<td style="border:1px solid #e8ecf1;padding:4px 8px;">${trimmed}</td>`
    }).join('') + '</tr>'
  })
  // 换行
  html = html.replace(/\n\n/g, '</p><p>')
  html = html.replace(/\n/g, '<br/>')
  html = '<p>' + html + '</p>'

  // 包装表格
  html = html.replace(/((?:<tr>.*?<\/tr>\s*)+)/g, '<table style="border-collapse:collapse;margin:8px 0;">$1</table>')

  return html
}

/** 滚动到底部 */
function scrollToBottom() {
  nextTick(() => {
    if (messageListRef.value) {
      messageListRef.value.scrollTop = messageListRef.value.scrollHeight
    }
  })
}

/** Agent 多步推理分析 */
async function handleAgentAnalyze() {
  const question = inputText.value.trim()
  if (!question || !currentSessionId.value || streaming.value) return

  messages.value.push({ role: 'user', content: '[Agent分析] ' + question, id: Date.now() })
  inputText.value = ''
  scrollToBottom()

  const assistantMsg: any = { role: 'assistant', content: '', sources: [], id: null, feedback: null }
  messages.value.push(assistantMsg)

  streaming.value = true
  assistantMsg.content = '🔄 **正在进行多步推理分析...**\n\n1. 拆解问题为子任务\n2. 并行检索相关财报内容\n3. 交叉验证数据一致性\n4. 综合分析生成报告\n\n---\n'

  try {
    const docIdsStr = selectedDocIds.value.length > 0 ? selectedDocIds.value.join(',') : undefined
    const res: any = await agentAnalyzeApi(question, docIdsStr)
    if (res.code === 0) {
      const report = res.data.final_report || '分析报告生成失败'
      const subs = res.data.sub_questions || []
      assistantMsg.content = '## 📊 多步推理分析报告\n\n'
      if (subs.length > 0) {
        assistantMsg.content += '### 拆解的子问题：\n' + subs.map((s: any) => `- ${s.index}. ${s.question}`).join('\n') + '\n\n---\n\n'
      }
      assistantMsg.content += report
    }
  } catch {
    assistantMsg.content += '\n\n⚠️ Agent分析请求失败'
  }
  streaming.value = false
  scrollToBottom()
}

/** 消息反馈 */
async function handleFeedback(msg: any, rating: 'up' | 'down') {
  if (!currentSessionId.value || !msg.id) return
  try {
    await submitFeedbackApi(currentSessionId.value, msg.id, rating)
    msg.feedback = rating
    ElMessage.success(rating === 'up' ? '感谢反馈' : '感谢反馈，我们会改进')
  } catch { /* ignore */ }
}

onMounted(async () => {
  await fetchDocs()
  await fetchSessions()
  // 默认进入最近的会话，或创建新会话
  if (sessions.value.length > 0) {
    switchSession(sessions.value[0].id)
  } else {
    handleNewSession()
  }
})
</script>

<style scoped>
.chat-container {
  display: flex; height: calc(100vh - 120px); gap: 0;
  background: #fff; border-radius: 8px; overflow: hidden;
  border: 1px solid var(--border-light);
  box-shadow: 0 2px 8px rgba(13,27,54,0.04);
}

/* 左侧会话列表 */
.chat-sidebar {
  width: 260px; border-right: 1px solid var(--border-light);
  display: flex; flex-direction: column; background: #fafbfc;
}
.sidebar-header { padding: 12px; border-bottom: 1px solid var(--border-light); }
.session-list { flex: 1; overflow-y: auto; }
.session-item {
  padding: 10px 12px; cursor: pointer; border-bottom: 1px solid #f0f2f5;
  display: flex; justify-content: space-between; align-items: center;
  transition: background 0.2s;
}
.session-item:hover { background: #f0f4fb; }
.session-item.active { background: #e8f0fa; border-left: 3px solid #1a3c6e; }
.session-title { font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; color: var(--text-primary); }

/* 右侧对话区 */
.chat-main { flex: 1; display: flex; flex-direction: column; }
.message-list { flex: 1; overflow-y: auto; padding: 16px; background: #fafbfd; }
.message-item { display: flex; gap: 12px; margin-bottom: 20px; }
.message-item.user { flex-direction: row-reverse; }
.message-item.user .message-body { text-align: right; }
.message-body { max-width: 70%; }
.message-content {
  padding: 10px 14px; border-radius: 10px;
  font-size: 14px; line-height: 1.6; word-break: break-word;
}
.message-item.assistant .message-content {
  background: #fff; border: 1px solid var(--border-light); color: var(--text-primary);
}
.message-item.user .message-content {
  background: #1a3c6e; color: #fff;
}
.message-item.assistant .message-avatar {
  border: 2px solid #c8a951; border-radius: 50%; padding: 2px;
}
.message-sources { margin-top: 6px; }
.message-actions { margin-top: 4px; }

/* 输入区 */
.message-input {
  padding: 12px 16px; border-top: 1px solid var(--border-light);
  background: #fff;
}

/* Markdown */
.markdown-body pre {
  background: #f5f7fa; padding: 10px; border-radius: 4px; overflow-x: auto;
}
.markdown-body code {
  background: #f0f2f5; padding: 2px 6px; border-radius: 3px;
  font-family: monospace; color: #1a3c6e;
}
.markdown-body table { border-collapse: collapse; width: 100%; }
.markdown-body td, .markdown-body th {
  border: 1px solid var(--border-light); padding: 6px 10px;
}
</style>
