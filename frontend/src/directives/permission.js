/**
 * 权限指令
 * 
 * 使用方式：
 * v-permission="'instance:delete'"  - 单个权限
 * v-permission="['instance:delete', 'instance:update']"  - 多个权限（满足其一即可）
 * v-role="'super_admin'"  - 单个角色
 * v-role="['super_admin', 'approval_admin']"  - 多个角色（满足其一即可）
 */
import { useUserStore } from '@/stores/user'

/**
 * 权限指令
 */
export const permission = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const { value } = binding
    
    if (!value) return
    
    const permissions = Array.isArray(value) ? value : [value]
    const hasPermission = permissions.some(p => userStore.hasPermission(p))
    
    if (!hasPermission) {
      el.parentNode?.removeChild(el)
    }
  }
}

/**
 * 角色指令
 */
export const role = {
  mounted(el, binding) {
    const userStore = useUserStore()
    const { value } = binding
    
    if (!value) return
    
    const roles = Array.isArray(value) ? value : [value]
    const hasRole = roles.some(r => userStore.user?.role === r)
    
    if (!hasRole) {
      el.parentNode?.removeChild(el)
    }
  }
}

/**
 * 注册全局指令
 */
export function setupPermissionDirectives(app) {
  app.directive('permission', permission)
  app.directive('role', role)
}

export default {
  permission,
  role,
  setupPermissionDirectives
}
