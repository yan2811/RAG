<!--
  登录页面
  支持登录和注册双模式切换，图形验证码防攻击
-->
<template>
  <div class="login-wrapper">
    <!-- 背景装饰 -->
    <div class="bg-shapes">
      <div class="shape shape-1" />
      <div class="shape shape-2" />
      <div class="shape shape-3" />
    </div>

    <div class="login-card">
      <!-- Logo -->
      <div class="logo-area">
        <img src="@/assets/logo.png" alt="Logo" class="logo-img" />
      </div>

      <!-- 标题 -->
      <div class="login-header">
        <h2>财报 RAG 知识库系统</h2>
        <p>基于检索增强生成的智能财报分析平台</p>
      </div>

      <!-- 登录/注册表单 -->
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @keydown.enter="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <!-- 注册模式下显示邮箱 -->
        <el-form-item v-if="isRegister" label="邮箱（选填）" prop="email">
          <el-input v-model="form.email" placeholder="请输入邮箱" :prefix-icon="Message" />
        </el-form-item>

        <!-- 图形验证码（登录模式） -->
        <el-form-item v-if="!isRegister" label="验证码" prop="captchaCode">
          <div class="captcha-row">
            <el-input
              v-model="form.captchaCode"
              placeholder="请输入验证码"
              maxlength="4"
              style="width: 55%"
            />
            <img
              :src="captchaImage"
              alt="验证码"
              class="captcha-img"
              title="点击刷新验证码"
              @click="refreshCaptcha"
            />
          </div>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :loading="loading"
            style="width: 100%"
            @click="handleSubmit"
          >
            {{ isRegister ? '注 册' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <!-- 切换登录/注册 -->
      <div class="login-footer">
        <span v-if="!isRegister">
          还没有账号？
          <el-button type="primary" link @click="switchMode(true)">立即注册</el-button>
        </span>
        <span v-else>
          已有账号？
          <el-button type="primary" link @click="switchMode(false)">去登录</el-button>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { User, Lock, Message } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { getCaptchaApi } from '@/api/auth'

const router = useRouter()
const userStore = useUserStore()

const isRegister = ref(false)
const loading = ref(false)
const formRef = ref<FormInstance>()

const captchaId = ref('')
const captchaImage = ref('')

const form = reactive({
  username: '',
  password: '',
  email: '',
  captchaCode: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 64, message: '用户名长度 3-64 字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, max: 20, message: '密码长度 8-20 字符', trigger: 'blur' },
  ],
  captchaCode: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { min: 4, max: 4, message: '验证码为 4 位', trigger: 'blur' },
  ],
}

/** 刷新验证码 */
async function refreshCaptcha() {
  try {
    const res: any = await getCaptchaApi()
    const data = res.code === 0 ? res.data : res
    captchaId.value = data.captcha_id
    captchaImage.value = data.image
    form.captchaCode = ''
  } catch {
    // ignore
  }
}

/** 切换登录/注册模式 */
function switchMode(register: boolean) {
  isRegister.value = register
  form.captchaCode = ''
  if (register) {
    captchaImage.value = ''
  } else {
    refreshCaptcha()
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    loading.value = true
    try {
      if (isRegister.value) {
        if (!(/[a-zA-Z]/.test(form.password) && /\d/.test(form.password))) {
          ElMessage.error('密码必须同时包含字母和数字')
          loading.value = false
          return
        }
        await userStore.register(form.username, form.password, form.email || undefined)
        ElMessage.success('注册成功，已自动登录')
      } else {
        await userStore.login(form.username, form.password, captchaId.value, form.captchaCode)
        ElMessage.success('登录成功')
      }
      router.push('/dashboard')
    } catch (e: any) {
      // 登录失败刷新验证码
      if (!isRegister.value) await refreshCaptcha()
    } finally {
      loading.value = false
    }
  })
}

onMounted(() => {
  if (!isRegister.value) {
    refreshCaptcha()
  }
})
</script>

<style scoped>
/* ===== 全屏背景 ===== */
.login-wrapper {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: url('@/assets/login-bg.png') center / cover no-repeat;
  position: relative;
  overflow: hidden;
}

/* 背景装饰几何形状 */
.bg-shapes {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
.shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.08;
}
.shape-1 {
  width: 600px;
  height: 600px;
  background: #e94560;
  top: -200px;
  right: -150px;
  animation: float 20s ease-in-out infinite;
}
.shape-2 {
  width: 400px;
  height: 400px;
  background: #533483;
  bottom: -100px;
  left: -100px;
  animation: float 25s ease-in-out infinite reverse;
}
.shape-3 {
  width: 300px;
  height: 300px;
  background: #0f3460;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  animation: float 18s ease-in-out infinite;
}
@keyframes float {
  0%, 100% { transform: translate(0, 0) scale(1); }
  33% { transform: translate(30px, -30px) scale(1.05); }
  66% { transform: translate(-20px, 20px) scale(0.95); }
}

/* ===== 卡片 ===== */
.login-card {
  width: 440px;
  padding: 36px 40px 32px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1);
  position: relative;
  z-index: 1;
  animation: cardIn 0.6s ease-out;
}
@keyframes cardIn {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ===== Logo ===== */
.logo-area {
  text-align: center;
  margin-bottom: 8px;
}
.logo-img {
  width: 72px;
  height: 72px;
  object-fit: contain;
  border-radius: 16px;
}

/* ===== 标题 ===== */
.login-header {
  text-align: center;
  margin-bottom: 28px;
}
.login-header h2 {
  color: #1a1a2e;
  font-size: 22px;
  margin-bottom: 6px;
  font-weight: 700;
}
.login-header p {
  color: #909399;
  font-size: 13px;
}

/* ===== 验证码 ===== */
.captcha-row {
  display: flex;
  gap: 12px;
  align-items: center;
}
.captcha-img {
  width: 42%;
  height: 42px;
  border-radius: 6px;
  cursor: pointer;
  border: 1px solid #dcdfe6;
  object-fit: cover;
  transition: border-color 0.2s;
}
.captcha-img:hover {
  border-color: #409eff;
}

/* ===== 底部 ===== */
.login-footer {
  text-align: center;
  color: #909399;
  font-size: 13px;
  margin-top: 4px;
}

/* ===== 深色表单适配 ===== */
:deep(.el-form-item__label) {
  color: #303133;
  font-weight: 500;
}
</style>
