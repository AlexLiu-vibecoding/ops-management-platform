<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <!-- Logo区域 -->
      <div class="logo-section" :class="{ collapsed: isCollapse }">
        <div class="logo-icon">
          <el-icon :size="22"><Coin /></el-icon>
        </div>
        <transition name="fade">
          <div v-if="!isCollapse" class="logo-text">
            <span class="title">OpsCenter</span>
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
      
      <!-- 折叠按钮 -->
      <div class="collapse-btn" @click="isCollapse = !isCollapse">
        <el-icon :size="18">
          <Fold v-if="!isCollapse" />
          <Expand v-else />
        </el-icon>
      </div>
    </el-aside>
    
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header class="header">
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
              <el-avatar :size="32" class="user-avatar">
                {{ userStore.user?.real_name?.charAt(0) || userStore.user?.username?.charAt(0) || 'A' }}
              </el-avatar>
              <span class="user-name">{{ userStore.user?.real_name || userStore.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">
                  <el-icon><Key /></el-icon>
                  {{ $t('user.password') || '修改密码' }}
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
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
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
    
    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialog.visible" :title="$t('user.password') || '修改密码'" width="420px">
      <el-form :model="passwordDialog.form" label-width="100px">
        <el-form-item :label="$t('user.password')">
          <el-input
            v-model="passwordDialog.form.oldPassword"
            type="password"
            show-password
            :placeholder="$t('common.pleaseInput')"
          />
        </el-form-item>
        <el-form-item :label="$t('user.password')">
          <el-input
            v-model="passwordDialog.form.newPassword"
            type="password"
            show-password
            :placeholder="$t('common.pleaseInput')"
          />
        </el-form-item>
        <el-form-item :label="$t('user.password')">
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
import { 
  Fold, Expand, ArrowDown, Coin, Key, SwitchButton
} from '@element-plus/icons-vue'
import LangSwitch from '@/components/LangSwitch.vue'

const { t } = useI18n()

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const dynamicMenus = ref([])

// 菜单名称翻译映射
const menuNameMap = {
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
// 主题色
$primary-color: #409eff;
$sidebar-bg: #001529;
$sidebar-active-bg: #1890ff;

.main-layout {
  height: 100vh;
}

// 侧边栏
.aside {
  background: $sidebar-bg;
  transition: width 0.2s;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

// Logo区域
.logo-section {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  
  &.collapsed {
    justify-content: center;
    padding: 0;
  }
  
  .logo-icon {
    width: 32px;
    height: 32px;
    border-radius: 6px;
    background: linear-gradient(135deg, #1890ff, #096dd9);
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
  }
  
  .logo-text {
    margin-left: 12px;
    white-space: nowrap;
    
    .title {
      font-size: 18px;
      font-weight: 600;
      color: white;
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
  
  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
    color: rgba(255, 255, 255, 0.65);
    background: transparent;
    margin: 0;
    
    &:hover {
      background: rgba(255, 255, 255, 0.08);
      color: white;
    }
    
    .el-icon {
      color: inherit;
    }
  }
  
  :deep(.el-menu-item.is-active) {
    background: $sidebar-active-bg;
    color: white;
  }
  
  :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
    color: white;
  }
  
  // 子菜单
  :deep(.el-menu--inline) {
    background: rgba(0, 0, 0, 0.2);
    
    .el-menu-item {
      height: 44px;
      line-height: 44px;
      padding-left: 54px !important;
      
      &:hover {
        background: rgba(255, 255, 255, 0.05);
      }
      
      &.is-active {
        background: $sidebar-active-bg;
      }
    }
  }
}

// 折叠按钮
.collapse-btn {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  
  &:hover {
    color: white;
    background: rgba(255, 255, 255, 0.05);
  }
}

// 主容器
.main-container {
  display: flex;
  flex-direction: column;
  background: #f0f2f5;
}

// 顶部导航
.header {
  height: 56px;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-left {
    :deep(.el-breadcrumb) {
      font-size: 14px;
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .header-lang {
      margin-right: 8px;
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      cursor: pointer;
      padding: 6px 12px;
      border-radius: 6px;
      transition: background 0.2s;
      
      &:hover {
        background: #f5f7fa;
      }
      
      .user-avatar {
        background: $primary-color;
        color: white;
        font-size: 13px;
      }
      
      .user-name {
        font-size: 14px;
        color: #333;
      }
    }
  }
}

// 主内容区
.main {
  flex: 1;
  padding: 16px;
  overflow: auto;
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
