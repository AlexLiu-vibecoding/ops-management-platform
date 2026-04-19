import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { permissionApi } from '@/api/permissions'
import router from '@/router'

/**
 * 解析 JWT Token
 */
function parseJwt(token) {
  try {
    const base64Url = token.split('.')[1]
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(atob(base64).split('').map(function(c) {
      return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2)
    }).join(''))
    return JSON.parse(jsonPayload)
  } catch (e) {
    return null
  }
}

/**
 * 检查 Token 是否过期
 */
function isTokenExpired(token) {
  if (!token) return true
  const payload = parseJwt(token)
  if (!payload || !payload.exp) return true
  // exp 是秒级时间戳，需要乘以 1000 转换为毫秒
  return Date.now() >= payload.exp * 1000
}

/**
 * 清除过期的登录状态
 */
function clearExpiredAuth() {
  const token = localStorage.getItem('token')
  if (token && isTokenExpired(token)) {
    console.log('[Auth] Token 已过期，清除登录状态')
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    return true
  }
  return false
}

// 页面加载时检查并清除过期 token
clearExpiredAuth()

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))
  const permissions = ref([])
  const environmentIds = ref([])

  const isLoggedIn = computed(() => {
    // 不仅检查 token 是否存在，还要检查是否过期
    if (!token.value) return false
    return !isTokenExpired(token.value)
  })
  
  /** @deprecated 组件中请使用 hasPermission() 替代，isAdmin 仅作为内部快捷判断 */
  const isAdmin = computed(() => user.value?.role === 'super_admin')
  
  // 操作权限：超级管理员、审批管理员、运维人员可以操作实例
  const canOperate = computed(() => {
    const role = user.value?.role
    return ['super_admin', 'approval_admin', 'operator'].includes(role)
  })
  
  // 审批权限
  const canApprove = computed(() => {
    const role = user.value?.role
    return ['super_admin', 'approval_admin'].includes(role)
  })
  
  /** 基于权限码判断能否创建实例 */
  const canCreateInstance = computed(() => hasPermission('instance:create'))
  /** 基于权限码判断能否管理Redis */
  const canManageRedis = computed(() => hasPermission('instance:redis_manage'))
  /** 基于权限码判断能否审批变更 */
  const canApproveChange = computed(() => hasPermission('approval:approve'))
  
  // 检查是否有某个权限
  const hasPermission = (permissionCode) => {
    if (isAdmin.value) return true
    return permissions.value.includes(permissionCode)
  }
  
  // 检查是否有环境访问权限
  const hasEnvironmentAccess = (envId) => {
    if (isAdmin.value) return true
    return environmentIds.value.includes(envId)
  }

  async function login(username, password) {
    try {
      const res = await authApi.login({ username, password })
      token.value = res.access_token
      user.value = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      // 登录成功后获取权限
      await fetchPermissions()
      return { success: true }
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '登录失败' }
    }
  }
  
  // 获取用户权限
  async function fetchPermissions() {
    try {
      const res = await permissionApi.getPermissions()
      permissions.value = res.permissions || []
      environmentIds.value = res.environment_ids || []
    } catch (error) {
      console.error('获取权限失败:', error)
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    permissions.value = []
    environmentIds.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  function checkAuth() {
    // 先检查 token 是否过期
    if (isTokenExpired(token.value)) {
      logout()
      return
    }
    
    if (token.value && !user.value) {
      // 有token但没有用户信息，尝试获取
      authApi.getCurrentUser()
        .then(res => {
          user.value = res
          localStorage.setItem('user', JSON.stringify(res))
          // 获取权限
          fetchPermissions()
        })
        .catch(() => {
          logout()
        })
    } else if (token.value && permissions.value.length === 0) {
      // 有 token 但没有权限信息，获取权限
      fetchPermissions()
    }
  }

  return {
    token,
    user,
    permissions,
    environmentIds,
    isLoggedIn,
    isAdmin,
    canOperate,
    canApprove,
    canCreateInstance,
    canManageRedis,
    canApproveChange,
    hasPermission,
    hasEnvironmentAccess,
    login,
    logout,
    checkAuth,
    fetchPermissions
  }
})
