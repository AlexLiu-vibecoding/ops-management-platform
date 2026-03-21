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
        meta: { title: 'Dashboard', icon: 'DataAnalysis' }
      },
      {
        path: 'instances',
        name: 'Instances',
        component: () => import('@/views/instances/index.vue'),
        meta: { title: 'Instances', icon: 'Server', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'instances/:id',
        name: 'InstanceDetail',
        component: () => import('@/views/instances/detail.vue'),
        meta: { title: 'Instance Detail', hidden: true, roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'environments',
        name: 'Environments',
        component: () => import('@/views/environments/index.vue'),
        meta: { title: 'Environments', icon: 'Collection', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'sql-editor',
        name: 'SqlEditor',
        component: () => import('@/views/sql-editor/index.vue'),
        meta: { title: 'SQL Editor', icon: 'Document' }
      },
      {
        path: 'approvals',
        name: 'Approvals',
        component: () => import('@/views/approvals/index.vue'),
        meta: { title: 'Approvals', icon: 'Stamp' }
      },
      {
        path: 'monitor',
        name: 'Monitor',
        redirect: '/monitor/performance',
        meta: { title: 'Monitor', icon: 'Monitor' },
        children: [
          {
            path: 'performance',
            name: 'Performance',
            component: () => import('@/views/monitor/performance.vue'),
            meta: { title: 'Performance' }
          },
          {
            path: 'slow-query',
            name: 'SlowQuery',
            component: () => import('@/views/monitor/slow-query.vue'),
            meta: { title: 'Slow Query' }
          },
          {
            path: 'settings',
            name: 'MonitorSettings',
            component: () => import('@/views/monitor/settings.vue'),
            meta: { title: 'Monitor Settings' }
          }
        ]
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/index.vue'),
        meta: { title: 'Users', icon: 'User', roles: ['super_admin'] }
      },
      {
        path: 'registrations',
        name: 'Registrations',
        component: () => import('@/views/registrations/index.vue'),
        meta: { title: 'Registrations', icon: 'UserFilled', roles: ['super_admin'] }
      },
      {
        path: 'menu-config',
        name: 'MenuConfig',
        component: () => import('@/views/menu-config/index.vue'),
        meta: { title: 'Menu Config', icon: 'Menu', roles: ['super_admin'] }
      },
      {
        path: 'notification',
        name: 'Notification',
        component: () => import('@/views/notification/index.vue'),
        meta: { title: 'Notification', icon: 'ChatDotRound', roles: ['super_admin'] }
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/views/audit/index.vue'),
        meta: { title: 'Audit Logs', icon: 'Tickets' }
      },
      {
        path: 'scripts',
        name: 'Scripts',
        component: () => import('@/views/scripts/index.vue'),
        meta: { title: 'Scripts', icon: 'DocumentCopy', roles: ['super_admin', 'approval_admin', 'operator'] }
      },
      {
        path: 'scheduled-tasks',
        name: 'ScheduledTasks',
        component: () => import('@/views/scheduled-tasks/index.vue'),
        meta: { title: 'Scheduled Tasks', icon: 'Timer', roles: ['super_admin', 'approval_admin', 'operator'] }
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
