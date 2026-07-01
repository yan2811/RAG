/**
 * 智能问答 API（M4+M8）
 */
import request from '@/utils/request'
import { useUserStore } from '@/stores/user'

/** 获取会话列表 */
export function getSessionsApi(params?: any) {
  return request.get('/sessions', { params })
}

/** 创建新会话 */
export function createSessionApi(title?: string) {
  return request.post('/sessions', null, { params: { title } })
}

/** 更新会话标题 */
export function updateSessionApi(id: number, title: string) {
  return request.put(`/sessions/${id}`, null, { params: { title } })
}

/** 删除会话 */
export function deleteSessionApi(id: number) {
  return request.delete(`/sessions/${id}`)
}

/** 获取会话消息历史 */
export function getMessagesApi(sessionId: number, params?: any) {
  return request.get(`/sessions/${sessionId}/messages`, { params })
}

/** 导出会话为 Markdown */
export function exportSessionApi(sessionId: number) {
  return request.get(`/sessions/${sessionId}/export`)
}

/** 发送消息（SSE 流式） */
export function sendMessageSSE(
  sessionId: number,
  question: string,
  documentIds?: number[],
  onSource: (data: any) => void = () => {},
  onAnswer: (chunk: string) => void = () => {},
  onDone: (messageId: number) => void = () => {},
  onError: (err: string) => void = () => {},
) {
  const token = localStorage.getItem('token') || ''
  const params = new URLSearchParams({ question })
  if (documentIds?.length) {
    params.set('document_ids', documentIds.join(','))
  }

  fetch(`/api/v1/chat/${sessionId}?${params.toString()}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
  }).then(async (response) => {
    if (!response.ok) {
      const err = await response.text()
      onError(`请求失败 (${response.status}): ${err}`)
      return
    }
    const reader = response.body?.getReader()
    if (!reader) { onError('无法读取响应流'); return }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // 解析 SSE 事件
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'mode' || data.type === 'sources') onSource(data)
            else if (data.type === 'answer') onAnswer(data.content || '')
            else if (data.type === 'done') onDone(data.message_id || 0)
          } catch { /* skip parse errors */ }
        }
      }
    }
  }).catch((err) => {
    onError(`网络错误: ${err.message}`)
  })
}

/** 提交消息反馈 */
export function submitFeedbackApi(sessionId: number, messageId: number, rating: 'up' | 'down', reason?: string) {
  return request.post(`/chat/${sessionId}/feedback`, null, {
    params: { message_id: messageId, rating, reason },
  })
}
