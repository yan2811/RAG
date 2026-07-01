/**
 * Axios 请求封装
 * - 自动注入 JWT Token
 * - 统一错误处理（401 跳转登录页）
 * - 响应数据自动解包
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@/router'

// 创建 Axios 实例
const request: AxiosInstance = axios.create({
  baseURL: '/api/v1',      // Vite 代理到 FastAPI 后端
  timeout: 30000,          // 30 秒超时
  headers: { 'Content-Type': 'application/json' },
})

/**
 * 请求拦截器：自动附加 JWT Token
 */
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

/**
 * 响应拦截器：统一处理错误
 */
request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data  // 自动解包 data
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      switch (status) {
        case 401:
          // Token 过期或无效 → 清除登录状态，跳转登录页
          localStorage.removeItem('token')
          localStorage.removeItem('user')
          router.push('/login')
          ElMessage.error('登录已过期，请重新登录')
          break
        case 403:
          ElMessage.error(data?.detail || '权限不足')
          break
        case 404:
          ElMessage.error(data?.detail || '请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器内部错误')
          break
        default:
          ElMessage.error(data?.detail || '请求失败')
      }
    } else {
      ElMessage.error('网络错误，请检查网络连接')
    }
    return Promise.reject(error)
  },
)

export default request
