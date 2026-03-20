import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import request from '@/api/index'

const routes = [
  {
    path: '/init',
    name: 'Init',
    component: () => import('@/views/init/index.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/index.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/dashboard',
    meta: { requiresAuth: true },
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'DataAnalysis' }
      },
      {
        path: 'instances',
        name: 'Instances',
        component: () => import('@/views/instances/index.vue'),
        meta: { title: '实例管理', icon: 'Server', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'instances/:id',
        name: 'InstanceDetail',
        component: () => import('@/views/instances/detail.vue'),
        meta: { title: '实例详情', hidden: true, roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'environments',
        name: 'Environments',
        component: () => import('@/views/environments/index.vue'),
        meta: { title: '环境管理', icon: 'Collection', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'sql-editor',
        name: 'SqlEditor',
        component: () => import('@/views/sql-editor/index.vue'),
        meta: { title: 'SQL编辑器', icon: 'Document' }
      },
      {
        path: 'approvals',
        name: 'Approvals',
        component: () => import('@/views/approvals/index.vue'),
        meta: { title: '变更审批', icon: 'Stamp' }
      },
      {
        path: 'monitor',
        name: 'Monitor',
        redirect: '/monitor/performance',
        meta: { title: '监控中心', icon: 'Monitor' },
        children: [
          {
            path: 'performance',
            name: 'Performance',
            component: () => import('@/views/monitor/performance.vue'),
            meta: { title: '性能监控' }
          },
          {
            path: 'slow-query',
            name: 'SlowQuery',
            component: () => import('@/views/monitor/slow-query.vue'),
            meta: { title: '慢查询监控' }
          },
          {
            path: 'settings',
            name: 'MonitorSettings',
            component: () => import('@/views/monitor/settings.vue'),
            meta: { title: '监控配置' }
          }
        ]
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['super_admin'] }
      },
      {
        path: 'registrations',
        name: 'Registrations',
        component: () => import('@/views/registrations/index.vue'),
        meta: { title: '注册审批', icon: 'UserFilled', roles: ['super_admin'] }
      },
      {
        path: 'menu-config',
        name: 'MenuConfig',
        component: () => import('@/views/menu-config/index.vue'),
        meta: { title: '菜单配置', icon: 'Menu', roles: ['super_admin'] }
      },
      {
        path: 'notification',
        name: 'Notification',
        component: () => import('@/views/notification/index.vue'),
        meta: { title: '通知管理', icon: 'ChatDotRound', roles: ['super_admin'] }
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/index.vue'),
        meta: { title: '审计日志', icon: 'Tickets' }
      },
      {
        path: 'scripts',
        name: 'Scripts',
        component: () => import('@/views/scripts/index.vue'),
        meta: { title: '脚本管理', icon: 'DocumentCopy', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'scheduled-tasks',
        name: 'ScheduledTasks',
        component: () => import('@/views/scheduled-tasks/index.vue'),
        meta: { title: '定时任务', icon: 'Timer', roles: ['super_admin', 'approval_admin', 'operator'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 检查系统初始化状态
let initChecked = false
let isInitialized = null

async function checkInitStatus() {
  if (initChecked) return isInitialized
  
  try {
    const status = await request.get('/init/status')
    isInitialized = status.is_initialized
  } catch (error) {
    // 如果检查失败，假设已初始化（避免阻塞）
    isInitialized = true
  }
  
  initChecked = true
  return isInitialized
}

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // 检查初始化状态（仅首次）
  if (!initChecked && to.path !== '/init') {
    const initialized = await checkInitStatus()
    if (!initialized) {
      next('/init')
      return
    }
  }
  
  // 初始化页面
  if (to.path === '/init') {
    if (isInitialized) {
      next('/login')
    } else {
      next()
    }
    return
  }
  
  // 不需要认证的页面
  if (to.meta.requiresAuth === false) {
    if (to.path === '/login' && userStore.isLoggedIn) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }
  
  // 需要认证的页面
  if (!userStore.isLoggedIn) {
    next('/login')
    return
  }
  
  // 权限检查
  if (to.meta.roles && !to.meta.roles.includes(userStore.user?.role)) {
    next('/dashboard')
    return
  }
  
  next()
})

export default router
