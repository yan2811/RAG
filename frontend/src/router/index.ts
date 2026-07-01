/**
 * Vue Router 路由配置
 * - 基于权限的路由守卫（未登录跳转登录页）
 * - 懒加载页面组件（优化首屏加载速度）
 */
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'

// 路由表
const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/LoginView.vue'),
    meta: { title: '登录', noAuth: true },
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('@/components/layout/AppLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/DashboardView.vue'),
        meta: { title: '首页工作台', icon: 'HomeFilled' },
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/documents/DocumentList.vue'),
        meta: { title: '文档管理', icon: 'Document' },
      },
      {
        path: 'documents/upload',
        name: 'DocumentUpload',
        component: () => import('@/views/documents/DocumentUpload.vue'),
        meta: { title: '上传文档', hidden: true },
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/documents/DocumentDetail.vue'),
        meta: { title: '文档详情', hidden: true },
      },
      {
        path: 'knowledge',
        name: 'Knowledge',
        component: () => import('@/views/knowledge/KnowledgeOverview.vue'),
        meta: { title: '知识库管理', icon: 'Collection' },
      },
      {
        path: 'knowledge/tags',
        name: 'Tags',
        component: () => import('@/views/knowledge/TagManagement.vue'),
        meta: { title: '标签管理', hidden: true },
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/chat/ChatLayout.vue'),
        meta: { title: '智能问答', icon: 'ChatDotRound' },
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportList.vue'),
        meta: { title: '报告中心', icon: 'Tickets' },
      },
      {
        path: 'bigscreen',
        name: 'BigScreen',
        component: () => import('@/views/analytics/BigScreen.vue'),
        meta: { title: '数据可视化大屏', icon: 'Monitor', hidden: true },
      },
      {
        path: 'analytics/:docId?',
        name: 'Analytics',
        component: () => import('@/views/analytics/AnalyticsDashboard.vue'),
        meta: { title: '分析仪表盘', icon: 'DataAnalysis' },
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/admin/UserProfile.vue'),
        meta: { title: '个人主页', hidden: true },
      },
      {
        path: 'admin/users',
        name: 'AdminUsers',
        component: () => import('@/views/admin/UserManagement.vue'),
        meta: { title: '用户管理', icon: 'User', permission: 'admin:users' },
      },
      {
        path: 'admin/roles',
        name: 'AdminRoles',
        component: () => import('@/views/admin/RoleManagement.vue'),
        meta: { title: '角色管理', icon: 'Avatar', permission: 'admin:roles' },
      },
      {
        path: 'admin/logs',
        name: 'AdminLogs',
        component: () => import('@/views/admin/OperationLogs.vue'),
        meta: { title: '操作日志', icon: 'Notebook', permission: 'admin:logs' },
      },
      {
        path: 'admin/settings',
        name: 'AdminSettings',
        component: () => import('@/views/admin/SystemSettings.vue'),
        meta: { title: '系统配置', icon: 'Setting', permission: 'admin:settings' },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

/**
 * 全局路由守卫：检查登录状态和页面标题
 */
router.beforeEach((to, from, next) => {
  // 设置页面标题
  document.title = (to.meta.title as string) || '财报 RAG 知识库系统'

  // 不需要认证的页面（登录页）直接放行
  if (to.meta.noAuth) {
    next()
    return
  }

  // 检查是否已登录
  const token = localStorage.getItem('token')
  if (!token) {
    next('/login')
    return
  }

  next()
})

export default router
