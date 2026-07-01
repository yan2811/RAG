<!--
  应用主布局 —— 淡蓝 + 金融金
  侧边栏深蓝 + 顶栏白色 + 内容区淡蓝
-->
<template>
  <el-container class="app-layout">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="app-aside">
      <div class="logo-area">
        <img src="@/assets/logo.png" alt="logo" class="logo-img" />
        <span v-show="!isCollapse" class="logo-title">财报RAG系统</span>
      </div>

      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="transparent"
        text-color="#b8c5d4"
        active-text-color="#c8a951"
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <span>首页工作台</span>
        </el-menu-item>
        <el-menu-item index="/documents">
          <el-icon><Document /></el-icon>
          <span>文档管理</span>
        </el-menu-item>
        <el-menu-item index="/knowledge">
          <el-icon><Collection /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/chat">
          <el-icon><ChatDotRound /></el-icon>
          <span>智能问答</span>
        </el-menu-item>
        <el-menu-item index="/analytics">
          <el-icon><DataAnalysis /></el-icon>
          <span>分析仪表盘</span>
        </el-menu-item>
        <el-menu-item index="/reports">
          <el-icon><Tickets /></el-icon>
          <span>报告中心</span>
        </el-menu-item>
        <el-menu-item index="/bigscreen">
          <el-icon><Monitor /></el-icon>
          <span>数据大屏</span>
        </el-menu-item>

        <el-sub-menu v-if="userStore.hasPermission('admin:users')" index="admin">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item v-if="userStore.hasPermission('admin:users')" index="/admin/users">用户管理</el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('admin:roles')" index="/admin/roles">角色管理</el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('admin:logs')" index="/admin/logs">操作日志</el-menu-item>
          <el-menu-item v-if="userStore.hasPermission('admin:settings')" index="/admin/settings">系统配置</el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="isCollapse = !isCollapse" :size="20">
            <Fold v-if="!isCollapse" /><Expand v-else />
          </el-icon>
          <span class="page-title">{{ currentTitle }}</span>
        </div>
        <div class="header-right">
          <el-avatar :size="30" :style="{ background: 'rgba(26,60,110,0.1)', color: '#1a3c6e', fontSize: '13px' }">
            {{ userStore.user?.username?.charAt(0)?.toUpperCase() || 'U' }}
          </el-avatar>
          <span class="username">{{ userStore.user?.username }}</span>
          <el-dropdown @command="handleCommand">
            <el-icon class="user-menu-icon" :size="16"><ArrowDown /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile"><el-icon><User /></el-icon>个人主页</el-dropdown-item>
                <el-dropdown-item command="logout" divided><el-icon><SwitchButton /></el-icon>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="app-main">
        <router-view v-slot="{ Component, route: r }">
          <transition mode="out-in"
            enter-active-class="animate__animated animate__fadeIn animate__faster"
            leave-active-class="animate__animated animate__fadeOut animate__faster">
            <component :is="Component" :key="r.fullPath" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)
const activeMenu = computed(() => route.path)
const currentTitle = computed(() => route.meta.title as string || '')

function handleCommand(command: string) {
  if (command === 'profile') { router.push('/profile') }
  else if (command === 'logout') { userStore.logout(); router.push('/login') }
}
</script>

<style scoped>
.app-layout { height: 100vh; }

.app-aside {
  background: linear-gradient(180deg, #0d1b36 0%, #111c32 100%);
  border-right: 1px solid rgba(200,169,81,0.08);
  overflow-y: auto; overflow-x: hidden; transition: width 0.3s;
}

.logo-area {
  height: 56px; display: flex; align-items: center; justify-content: center; gap: 8px;
  border-bottom: 1px solid rgba(200,169,81,0.12);
  background: rgba(0,0,0,0.15);
}
.logo-img { width: 28px; height: 28px; border-radius: 6px; }
.logo-title { color: #c8a951; font-size: 15px; font-weight: 600; white-space: nowrap; letter-spacing: 1px; }

/* 顶栏 */
.app-header {
  height: 50px; display: flex; align-items: center; justify-content: space-between;
  background: #fff; border-bottom: 1px solid var(--border-light);
  padding: 0 20px; box-shadow: 0 1px 4px rgba(13,27,54,0.04);
}
.header-left { display: flex; align-items: center; gap: 10px; }
.collapse-btn { cursor: pointer; color: var(--text-muted); transition: color 0.2s; }
.collapse-btn:hover { color: var(--el-color-primary); }
.page-title { font-size: 15px; font-weight: 500; color: var(--text-primary); }
.header-right { display: flex; align-items: center; gap: 10px; }
.username { font-size: 13px; color: var(--text-secondary); }
.user-menu-icon { color: var(--text-muted); cursor: pointer; transition: color 0.2s; }
.user-menu-icon:hover { color: var(--el-color-primary); }

/* 内容区 */
.app-main { background: var(--bg-page); padding: 16px 20px; overflow-y: auto; min-height: 0; }
</style>
