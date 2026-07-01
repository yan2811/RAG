/**
 * 认证相关 API
 */
import request from '@/utils/request'

/** 获取图形验证码 */
export function getCaptchaApi() {
  return request.get('/auth/captcha')
}

/** 用户登录 */
export function loginApi(data: {
  username: string
  password: string
  captcha_id: string
  captcha_code: string
}) {
  return request.post('/auth/login', data)
}

/** 用户注册 */
export function registerApi(data: { username: string; password: string; email?: string }) {
  return request.post('/auth/register', data)
}

/** 获取当前用户信息 */
export function getMeApi() {
  return request.get('/auth/me')
}
