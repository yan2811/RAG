<!--
  用户个人主页
  查看和修改个人信息、头像、密码
-->
<template>
  <div class="user-profile">
    <el-row :gutter="20">
      <!-- 个人信息卡片 -->
      <el-col :span="8">
        <el-card>
          <div style="text-align: center; padding: 20px 0;">
            <el-avatar :size="80" style="background: #409EFF; font-size: 32px;">
              {{ userStore.user?.username?.charAt(0)?.toUpperCase() }}
            </el-avatar>
            <h3 style="margin: 12px 0 4px;">{{ userStore.user?.username }}</h3>
            <p style="color: #909399; font-size: 13px;">{{ userStore.user?.email || '未设置邮箱' }}</p>
            <el-tag v-for="role in userStore.roles" :key="role" size="small" style="margin: 2px;">
              {{ roleMap[role] || role }}
            </el-tag>
          </div>
          <el-divider />
          <el-descriptions :column="1" size="small">
            <el-descriptions-item label="用户ID">{{ userStore.user?.id }}</el-descriptions-item>
            <el-descriptions-item label="账号状态">
              <el-tag :type="userStore.user?.status === 'active' ? 'success' : 'danger'" size="small">
                {{ userStore.user?.status === 'active' ? '正常' : '已禁用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="拥有权限">{{ userStore.permissions.length }} 项</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>

      <!-- 修改信息 -->
      <el-col :span="16">
        <el-card style="margin-bottom: 20px;">
          <template #header><span>修改个人信息</span></template>
          <el-form :model="profileForm" label-width="80px" style="max-width: 400px;">
            <el-form-item label="邮箱">
              <el-input v-model="profileForm.email" placeholder="请输入邮箱" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="updateProfile">保存修改</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card>
          <template #header><span>修改密码</span></template>
          <el-form :model="pwdForm" label-width="100px" style="max-width: 400px;">
            <el-form-item label="新密码">
              <el-input v-model="pwdForm.password" type="password" show-password placeholder="8-20字符，含字母和数字" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="updatePassword">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 权限列表 -->
        <el-card style="margin-top: 20px;">
          <template #header><span>我的权限</span></template>
          <el-tag v-for="perm in userStore.permissions" :key="perm" size="small" style="margin: 2px 4px;">
            {{ perm }}
          </el-tag>
          <el-empty v-if="!userStore.permissions.length" description="暂无特殊权限" :image-size="40" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { updateUserApi } from '@/api/admin'
import request from '@/utils/request'

const userStore = useUserStore()

const roleMap: Record<string, string> = {
  super_admin: '超级管理员', admin: '管理员', user: '普通用户', guest: '访客',
}

const profileForm = reactive({ email: userStore.user?.email || '' })
const pwdForm = reactive({ password: '' })

async function updateProfile() {
  if (!userStore.user) return
  try {
    await updateUserApi(userStore.user.id, { email: profileForm.email })
    // Refresh user info
    const res: any = await request.get('/auth/me')
    if (res.access_token || res.user) {
      const u = res.user || res
      localStorage.setItem('user', JSON.stringify(u))
      userStore.user = u
    }
    ElMessage.success('个人信息已更新')
  } catch { /* ignore */ }
}

async function updatePassword() {
  if (!pwdForm.password) return ElMessage.warning('请输入新密码')
  if (!/[a-zA-Z]/.test(pwdForm.password) || !/\d/.test(pwdForm.password)) {
    return ElMessage.error('密码需包含字母和数字')
  }
  if (!userStore.user) return
  try {
    await updateUserApi(userStore.user.id, { password: pwdForm.password })
    ElMessage.success('密码已修改，请重新登录')
    pwdForm.password = ''
    userStore.logout()
    window.location.href = '/login'
  } catch { /* ignore */ }
}
</script>
