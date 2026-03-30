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
            meta: { title: 'DB变更', icon: 'Coin' }
          },
          {
            path: 'redis-requests',
            name: 'RedisChangeRequests',
            component: () => import('@/views/change/redis-requests.vue'),
            meta: { title: 'Redis变更', icon: 'Key' }
          },
          {
            path: 'windows',
            name: 'ChangeWindows',
            component: () => import('@/views/change/windows/index.vue'),
            meta: { title: '变更窗口', icon: 'Clock' }
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
            path: 'alerts',
            name: 'Alerts',
            component: () => import('@/views/alerts/index.vue'),
            meta: { title: '告警中心', icon: 'Bell' }
          },
          {
            path: 'replication',
            name: 'Replication',
            component: () => import('@/views/replication/index.vue'),
            meta: { title: '主从复制', icon: 'Connection' }
          },
          {
            path: 'locks',
            name: 'Locks',
            component: () => import('@/views/locks/index.vue'),
            meta: { title: '事务与锁', icon: 'Lock' }
          },
          {
            path: 'inspection',
            name: 'Inspection',
            component: () => import('@/views/inspection/index.vue'),
            meta: { title: '巡检报告', icon: 'DocumentChecked' }
          },
          {
            path: 'scheduled-inspection',
            name: 'ScheduledInspection',
            component: () => import('@/views/inspection/scheduled/index.vue'),
            meta: { title: '定时巡检', icon: 'Timer' }
          },
          {
            path: 'alert-rules',
            name: 'AlertRules',
            component: () => import('@/views/alerts/rules/index.vue'),
            meta: { title: '告警规则', icon: 'Warning' }
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
      
      // 系统管理 - 用户管理（含注册审批）
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: '用户管理', icon: 'User', roles: ['super_admin'] }
      },
      // 系统管理 - 权限管理
      {
        path: 'permissions',
        name: 'Permissions',
        component: () => import('@/views/permissions/index.vue'),
        meta: { title: '权限管理', icon: 'Lock', roles: ['super_admin'] }
      },
      // 系统管理 - 菜单配置
      {
        path: 'menu-config',
        name: 'MenuConfig',
        component: () => import('@/views/menu-config/index.vue'),
        meta: { title: '菜单配置', icon: 'Menu', roles: ['super_admin'] }
      },
      // 系统管理 - 审计日志
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/index.vue'),
        meta: { title: '审计日志', icon: 'Tickets', roles: ['super_admin'] }
      },
      // 系统管理 - 系统设置（含后台任务、AWS区域管理等）
      {
        path: 'system',
        name: 'SystemSettings',
        component: () => import('@/views/system/index.vue'),
        meta: { title: '系统设置', icon: 'Tools', roles: ['super_admin'] }
      },
      
      // 配置管理
      {
        path: 'config',
        name: 'Config',
        redirect: '/config/notification',
        meta: { title: '配置管理', icon: 'Setting' },
        children: [
          {
            path: 'notification',
            name: 'NotificationConfig',
            component: () => import('@/views/config/notification.vue'),
            meta: { title: '通知管理', icon: 'Bell' }
          }
        ]
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
