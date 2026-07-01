/**
 * 用户状态管理（Pinia Store）
 * 管理用户登录状态、Token、角色权限
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { loginApi, registerApi } from '@/api/auth'

export interface UserInfo {
  id: number
  username: string
  email: string | null
  avatar: string | null
  status: string
  roles: string[]
  permissions: string[]
}

export const useUserStore = defineStore('user', () => {
  // ===== 状态 =====
  const token = ref<string>(localStorage.getItem('token') || '')
  const user = ref<UserInfo | null>(
    JSON.parse(localStorage.getItem('user') || 'null'),
  )

  // ===== 计算属性 =====
  const isLoggedIn = computed(() => !!token.value && !!user.value)
  const roles = computed(() => user.value?.roles || [])
  const permissions = computed(() => user.value?.permissions || [])

  /**
   * 检查用户是否拥有指定权限
   */
  function hasPermission(perm: string): boolean {
    // 超级管理员拥有所有权限
    if (roles.value.includes('super_admin')) return true
    return permissions.value.includes(perm)
  }

  /**
   * 用户登录
   */
  async function login(username: string, password: string, captchaId: string, captchaCode: string) {
    const res: any = await loginApi({ username, password, captcha_id: captchaId, captcha_code: captchaCode })
    // 兼容两种格式：直接返回 TokenResponse 或包裹 {code,data}
    const tokenData = res.code === 0 ? res.data : res
    if (tokenData.access_token) {
      token.value = tokenData.access_token
      user.value = tokenData.user
      localStorage.setItem('token', tokenData.access_token)
      localStorage.setItem('user', JSON.stringify(tokenData.user))
    }
    return res
  }

  /**
   * 用户注册
   */
  async function register(username: string, password: string, email?: string) {
    const res: any = await registerApi({ username, password, email })
    const tokenData = res.code === 0 ? res.data : res
    if (tokenData.access_token) {
      token.value = tokenData.access_token
      user.value = tokenData.user
      localStorage.setItem('token', tokenData.access_token)
      localStorage.setItem('user', JSON.stringify(tokenData.user))
    }
    return res
  }

  /**
   * 退出登录：清除 Token 和用户信息
   */
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }

  return { token, user, isLoggedIn, roles, permissions, hasPermission, login, register, logout }
})
