<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '72px' : '240px'" class="aside">
      <!-- Logo区域 -->
      <div class="logo-section" :class="{ collapsed: isCollapse }">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <transition name="fade">
          <div v-if="!isCollapse" class="logo-text">
            <span class="title">OpsCenter</span>
            <span class="subtitle">Database Platform</span>
          </div>
        </transition>
      </div>
      
      <!-- 菜单区域 -->
      <el-scrollbar class="menu-scrollbar">
        <el-menu
          :default-active="activeMenu"
          :collapse="isCollapse"
          :router="true"
          class="aside-menu"
        >
          <template v-for="item in menuItems" :key="item.path || item.id">
            <!-- 有子菜单 -->
            <el-sub-menu v-if="item.children && item.children.length > 0" :index="item.path || `menu-${item.id}`">
              <template #title>
                <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
                <span>{{ translateMenu(item.name) }}</span>
              </template>
              <el-menu-item
                v-for="child in item.children"
                :key="child.path"
                :index="child.path"
              >
                {{ translateMenu(child.name) }}
              </el-menu-item>
            </el-sub-menu>
            
            <!-- 无子菜单 -->
            <el-menu-item v-else :index="item.path || `menu-${item.id}`">
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <template #title>{{ translateMenu(item.name) }}</template>
            </el-menu-item>
          </template>
        </el-menu>
      </el-scrollbar>
      
      <!-- 底部区域 -->
      <div class="sidebar-footer">
        <!-- 折叠按钮 -->
        <button class="collapse-btn" @click="isCollapse = !isCollapse">
          <svg v-if="!isCollapse" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 19l-7-7 7-7M18 19l-7-7 7-7"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M13 17l5-5-5-5M6 17l5-5-5-5"/>
          </svg>
        </button>
      </div>
    </el-aside>
    
    <el-container class="main-container">
      <!-- 顶部导航 - 毛玻璃效果 -->
      <el-header class="header glass-header">
        <div class="header-left">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ translateMenu(item.title) }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <!-- 语言切换 -->
          <LangSwitch class="header-lang" />
          
          <!-- 用户信息 -->
          <el-dropdown @command="handleCommand" trigger="click">
            <div class="user-info">
              <el-avatar :size="36" class="user-avatar">
                {{ userStore.user?.real_name?.charAt(0) || userStore.user?.username?.charAt(0) || 'A' }}
              </el-avatar>
              <div class="user-detail">
                <span class="user-name">{{ userStore.user?.real_name || userStore.user?.username }}</span>
                <span class="user-role">{{ getRoleName(userStore.user?.role) }}</span>
              </div>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="dropdown-icon">
                <path d="M6 9l6 6 6-6"/>
              </svg>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                    <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                  </svg>
                  {{ $t('user.changePassword') || '修改密码' }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                    <polyline points="16 17 21 12 16 7"/>
                    <line x1="21" y1="12" x2="9" y2="12"/>
                  </svg>
                  {{ $t('nav.logout') }}
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 主内容区 -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
    
    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialog.visible" :title="$t('user.changePassword') || '修改密码'" width="420px">
      <el-form :model="passwordDialog.form" label-width="100px">
        <el-form-item :label="$t('user.oldPassword')">
          <el-input
            v-model="passwordDialog.form.oldPassword"
            type="password"
            show-password
            :placeholder="$t('common.pleaseInput')"
          />
        </el-form-item>
        <el-form-item :label="$t('user.newPassword')">
          <el-input
            v-model="passwordDialog.form.newPassword"
            type="password"
            show-password
            :placeholder="$t('common.pleaseInput')"
          />
        </el-form-item>
        <el-form-item :label="$t('user.confirmPassword')">
          <el-input
            v-model="passwordDialog.form.confirmPassword"
            type="password"
            show-password
            :placeholder="$t('common.pleaseInput')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialog.visible = false">{{ $t('common.cancel') }}</el-button>
        <el-button type="primary" @click="changePassword">{{ $t('common.confirm') }}</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import LangSwitch from '@/components/LangSwitch.vue'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const dynamicMenus = ref([])

// Menu name translation mapping
const menuNameMap = {
  // Chinese menu names (for backward compatibility)
  '仪表盘': 'nav.dashboard',
  '实例管理': 'nav.instances',
  'SQL编辑器': 'nav.sqlEditor',
  '变更审批': 'nav.approvals',
  '慢查询监控': 'nav.slowQuery',
  '性能监控': 'nav.performance',
  '脚本管理': 'nav.scripts',
  '定时任务': 'nav.scheduledTasks',
  '钉钉通知': 'nav.dingtalk',
  '用户管理': 'nav.users',
  '环境管理': 'nav.environments',
  '审计日志': 'nav.audit',
  '菜单配置': 'nav.menuConfig',
  '系统设置': 'nav.settings',
  '监控中心': 'nav.monitor',
  '监控配置': 'nav.monitorSettings',
  '注册审批': 'nav.registrations',
  '通知管理': 'nav.notification',
  '实例详情': 'nav.instanceDetail',
  // English menu names
  'Dashboard': 'nav.dashboard',
  'Instances': 'nav.instances',
  'SQL Editor': 'nav.sqlEditor',
  'Approvals': 'nav.approvals',
  'Slow Query': 'nav.slowQuery',
  'Performance': 'nav.performance',
  'Scripts': 'nav.scripts',
  'Scheduled Tasks': 'nav.scheduledTasks',
  'DingTalk': 'nav.dingtalk',
  'Users': 'nav.users',
  'Environments': 'nav.environments',
  'Audit Logs': 'nav.audit',
  'Menu Config': 'nav.menuConfig',
  'Settings': 'nav.settings',
  'Monitor': 'nav.monitor',
  'Monitor Settings': 'nav.monitorSettings',
  'Registrations': 'nav.registrations',
  'Notification': 'nav.notification',
  'Instance Detail': 'nav.instanceDetail',
}

// 翻译菜单名称
const translateMenu = (name) => {
  if (!name) return ''
  const key = menuNameMap[name]
  if (key) {
    return t(key)
  }
  return name
}

// 角色名称
const getRoleName = (role) => {
  const roles = {
    'super_admin': t('user.superAdmin'),
    'admin': t('user.admin'),
    'operator': t('user.operator'),
    'readonly': t('user.readonly')
  }
  return roles[role] || role
}

// 活动菜单
const activeMenu = computed(() => route.path)

// 面包屑
const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta?.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title
  }))
})

// 菜单项
const menuItems = computed(() => {
  if (dynamicMenus.value.length > 0) {
    return dynamicMenus.value
  }
  
  const routes = router.options.routes.find(r => r.path === '/')?.children || []
  
  return routes.filter(route => {
    if (route.meta?.hidden) return false
    if (route.meta?.roles) {
      return route.meta.roles.includes(userStore.user?.role)
    }
    return true
  }).map(route => ({
    id: route.path,
    name: route.meta?.title,
    path: route.path,
    icon: route.meta?.icon,
    children: route.children?.filter(child => !child.meta?.hidden).map(child => ({
      id: `${route.path}/${child.path}`,
      name: child.meta?.title,
      path: `${route.path}/${child.path}`,
      icon: child.meta?.icon
    }))
  }))
})

// 获取动态菜单
const fetchUserMenu = async () => {
  try {
    const menus = await request.get('/menu/user-menu')
    dynamicMenus.value = menus
  } catch (error) {
    console.warn('获取动态菜单失败:', error)
    dynamicMenus.value = []
  }
}

// 修改密码对话框
const passwordDialog = ref({
  visible: false,
  form: {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
})

// 处理下拉菜单命令
const handleCommand = (command) => {
  switch (command) {
    case 'password':
      passwordDialog.value.visible = true
      break
    case 'logout':
      ElMessageBox.confirm(t('login.logout') + '?', t('common.tip'), {
        type: 'warning'
      }).then(() => {
        userStore.logout()
      }).catch(() => {})
      break
  }
}

// 修改密码
const changePassword = async () => {
  const { oldPassword, newPassword, confirmPassword } = passwordDialog.value.form
  
  if (!oldPassword || !newPassword || !confirmPassword) {
    ElMessage.warning(t('common.pleaseInput'))
    return
  }
  
  if (newPassword !== confirmPassword) {
    ElMessage.warning(t('common.pleaseInput'))
    return
  }
  
  if (newPassword.length < 6) {
    ElMessage.warning(t('common.pleaseInput'))
    return
  }
  
  try {
    await authApi.changePassword(oldPassword, newPassword)
    ElMessage.success(t('common.success'))
    passwordDialog.value.visible = false
    userStore.logout()
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

onMounted(() => {
  fetchUserMenu()
})
</script>

<style lang="scss" scoped>
// ========================================
// iOS-Style Modern Layout
// ========================================

.main-layout {
  height: 100vh;
  background: var(--bg-primary);
}

// ========================================
// Sidebar / Aside
// ========================================
.aside {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 100;
}

// Logo区域
.logo-section {
  height: 72px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  margin-bottom: 8px;
  
  &.collapsed {
    justify-content: center;
    padding: 0;
  }
  
  .logo-icon {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    
    svg {
      width: 22px;
      height: 22px;
      color: white;
    }
  }
  
  .logo-text {
    margin-left: 14px;
    white-space: nowrap;
    
    .title {
      display: block;
      font-size: 18px;
      font-weight: 700;
      color: white;
      letter-spacing: -0.3px;
    }
    
    .subtitle {
      display: block;
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      margin-top: 2px;
      letter-spacing: 0.3px;
    }
  }
}

// 菜单滚动区域
.menu-scrollbar {
  flex: 1;
  overflow: hidden;
  
  :deep(.el-scrollbar__view) {
    height: 100%;
  }
}

// 菜单样式
.aside-menu {
  border-right: none;
  background: transparent;
  padding: 0 8px;
  
  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 44px;
    line-height: 44px;
    color: rgba(255, 255, 255, 0.65);
    background: transparent;
    margin: 4px 0;
    border-radius: 10px;
    padding: 0 16px !important;
    
    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: white;
    }
    
    .el-icon {
      color: inherit;
      font-size: 18px;
      margin-right: 12px;
    }
  }
  
  :deep(.el-menu-item.is-active) {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
  }
  
  :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
    color: white;
  }
  
  // 子菜单
  :deep(.el-menu--inline) {
    background: rgba(0, 0, 0, 0.15);
    border-radius: 10px;
    padding: 4px 0;
    margin: 4px 0;
    
    .el-menu-item {
      height: 40px;
      line-height: 40px;
      padding-left: 52px !important;
      margin: 2px 8px;
      border-radius: 8px;
      
      &:hover {
        background: rgba(255, 255, 255, 0.06);
      }
      
      &.is-active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      }
    }
  }
}

// 侧边栏底部
.sidebar-footer {
  padding: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  
  .collapse-btn {
    width: 100%;
    height: 40px;
    border: none;
    background: rgba(255, 255, 255, 0.08);
    border-radius: 10px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    
    svg {
      width: 20px;
      height: 20px;
      color: rgba(255, 255, 255, 0.65);
    }
    
    &:hover {
      background: rgba(255, 255, 255, 0.12);
      
      svg {
        color: white;
      }
    }
  }
}

// ========================================
// Main Container
// ========================================
.main-container {
  display: flex;
  flex-direction: column;
  background: var(--bg-primary);
}

// ========================================
// Header - Glass Effect
// ========================================
.header {
  height: 64px;
  background: var(--glass-bg);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 0.5px solid var(--separator);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  position: sticky;
  top: 0;
  z-index: 50;
  
  .header-left {
    :deep(.el-breadcrumb) {
      font-size: 14px;
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .header-lang {
      margin-right: 8px;
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      padding: 6px 12px 6px 6px;
      border-radius: 24px;
      transition: all 0.2s ease;
      background: transparent;
      
      &:hover {
        background: var(--bg-tertiary);
      }
      
      .user-avatar {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 14px;
        font-weight: 600;
      }
      
      .user-detail {
        display: flex;
        flex-direction: column;
        line-height: 1.2;
        
        .user-name {
          font-size: 14px;
          font-weight: 600;
          color: var(--text-primary);
        }
        
        .user-role {
          font-size: 11px;
          color: var(--text-secondary);
        }
      }
      
      .dropdown-icon {
        width: 16px;
        height: 16px;
        color: var(--text-secondary);
        margin-left: 4px;
      }
    }
  }
}

// ========================================
// Main Content
// ========================================
.main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  background: var(--bg-primary);
}

// ========================================
// Dropdown Menu Icons
// ========================================
:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 10px;
  
  svg {
    width: 16px;
    height: 16px;
  }
}

// ========================================
// Transitions
// ========================================
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-enter-active,
.page-leave-active {
  transition: all 0.25s ease-out;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
