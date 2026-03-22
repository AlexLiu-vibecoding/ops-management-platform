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
      // 仪表盘
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/index.vue'),
        meta: { title: '仪表盘', icon: 'DataAnalysis' }
      },
      
      // 数据管理 - 实例管理
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
        path: 'redis/:id',
        name: 'RedisDetail',
        component: () => import('@/views/instances/redis-detail.vue'),
        meta: { title: 'Redis详情', hidden: true, roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      // 数据管理 - 环境管理
      {
        path: 'environments',
        name: 'Environments',
        component: () => import('@/views/environments/index.vue'),
        meta: { title: '环境管理', icon: 'Collection', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      
      // SQL工具 - SQL编辑器
      {
        path: 'sql-editor',
        name: 'SqlEditor',
        component: () => import('@/views/sql-editor/index.vue'),
        meta: { title: 'SQL编辑器', icon: 'Edit' }
      },
      // SQL工具 - SQL优化器
      {
        path: 'sql-optimizer',
        name: 'SqlOptimizer',
        component: () => import('@/views/sql-optimizer/index.vue'),
        meta: { title: 'SQL优化器', icon: 'MagicStick' }
      },
      
      // 变更管理
      {
        path: 'change',
        name: 'Change',
        redirect: '/change/requests',
        meta: { title: '变更管理', icon: 'Stamp' },
        children: [
          {
            path: 'requests',
            name: 'ChangeRequests',
            component: () => import('@/views/change/requests.vue'),
            meta: { title: 'SQL变更申请', icon: 'EditPen' }
          },
          {
            path: 'redis-requests',
            name: 'RedisChangeRequests',
            component: () => import('@/views/change/redis-requests.vue'),
            meta: { title: 'Redis变更申请', icon: 'Key' }
          },
          {
            path: 'approvals',
            name: 'ChangeApprovals',
            component: () => import('@/views/change/approvals.vue'),
            meta: { title: '审批中心', icon: 'Checked', roles: ['super_admin', 'approval_admin'] }
          }
        ]
      },
      
      // 监控中心
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
            meta: { title: '性能监控', icon: 'TrendCharts' }
          },
          {
            path: 'slow-query',
            name: 'SlowQuery',
            component: () => import('@/views/monitor/slow-query.vue'),
            meta: { title: '慢查询监控', icon: 'Timer' }
          },
          {
            path: 'settings',
            name: 'MonitorSettings',
            component: () => import('@/views/monitor/settings.vue'),
            meta: { title: '监控配置', icon: 'Setting' }
          }
        ]
      },
      
      // 自动化 - 脚本管理
      {
        path: 'scripts',
        name: 'Scripts',
        component: () => import('@/views/scripts/index.vue'),
        meta: { title: '脚本管理', icon: 'DocumentCopy', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      // 自动化 - 定时任务
      {
        path: 'scheduled-tasks',
        name: 'ScheduledTasks',
        component: () => import('@/views/scheduled-tasks/index.vue'),
        meta: { title: '定时任务', icon: 'AlarmClock', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      
      // 系统管理 - 用户管理
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['super_admin'] }
      },
      // 系统管理 - 注册审批
      {
        path: 'registrations',
        name: 'Registrations',
        component: () => import('@/views/registrations/index.vue'),
        meta: { title: '注册审批', icon: 'UserFilled', roles: ['super_admin'] }
      },
      // 系统管理 - 菜单配置
      {
        path: 'menu-config',
        name: 'MenuConfig',
        component: () => import('@/views/menu-config/index.vue'),
        meta: { title: '菜单配置', icon: 'Menu', roles: ['super_admin'] }
      },
      // 系统管理 - 通知管理
      {
        path: 'notification',
        name: 'Notification',
        component: () => import('@/views/notification/index.vue'),
        meta: { title: '通知管理', icon: 'ChatDotRound', roles: ['super_admin'] }
      },
      // 系统管理 - 审计日志
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/index.vue'),
        meta: { title: '审计日志', icon: 'Tickets', roles: ['super_admin'] }
      },
      // 系统管理 - 系统设置
      {
        path: 'system',
        name: 'SystemSettings',
        component: () => import('@/views/system/index.vue'),
        meta: { title: '系统设置', icon: 'Tools', roles: ['super_admin'] }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Check system initialization status
let initChecked = false
let isInitialized = null

async function checkInitStatus() {
  if (initChecked) return isInitialized
  
  try {
    const status = await request.get('/init/status')
    isInitialized = status.is_initialized
  } catch (error) {
    // If check fails, assume initialized (to avoid blocking)
    isInitialized = true
  }
  
  initChecked = true
  return isInitialized
}

// Route guard
router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  
  // Check initialization status (only first time)
  if (!initChecked && to.path !== '/init') {
    const initialized = await checkInitStatus()
    if (!initialized) {
      next('/init')
      return
    }
  }
  
  // Initialization page
  if (to.path === '/init') {
    if (isInitialized) {
      next('/login')
    } else {
      next()
    }
    return
  }
  
  // Pages that don't require authentication
  if (to.meta.requiresAuth === false) {
    if (to.path === '/login' && userStore.isLoggedIn) {
      next('/dashboard')
    } else {
      next()
    }
    return
  }
  
  // Pages that require authentication
  if (!userStore.isLoggedIn) {
    next('/login')
    return
  }
  
  // Permission check
  if (to.meta.roles && !to.meta.roles.includes(userStore.user?.role)) {
    next('/dashboard')
    return
  }
  
  next()
})

export default router
