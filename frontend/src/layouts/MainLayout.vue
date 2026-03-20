<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '72px' : '240px'" class="aside">
      <!-- Logo区域 -->
      <div class="logo-section" :class="{ collapsed: isCollapse }">
        <div class="logo-icon">
          <div class="logo-bg">
            <el-icon :size="22"><Coin /></el-icon>
          </div>
        </div>
        <transition name="logo-fade">
          <div v-if="!isCollapse" class="logo-content">
            <span class="logo-text">OpsCenter</span>
            <span class="logo-subtitle">运维管理平台</span>
          </div>
        </transition>
      </div>
      
      <!-- 菜单区域 -->
      <div class="menu-wrapper">
        <el-scrollbar>
          <el-menu
            :default-active="activeMenu"
            :collapse="isCollapse"
            :router="true"
            class="aside-menu"
            :popper-class="menuPopperClass"
          >
            <template v-for="item in menuItems" :key="item.path || item.id">
              <!-- 有子菜单 -->
              <el-sub-menu v-if="item.children && item.children.length > 0" :index="item.path || `menu-${item.id}`">
                <template #title>
                  <div class="menu-item-content">
                    <el-icon v-if="item.icon" class="menu-icon"><component :is="item.icon" /></el-icon>
                    <span class="menu-title">{{ item.name }}</span>
                  </div>
                </template>
                <el-menu-item
                  v-for="child in item.children"
                  :key="child.path"
                  :index="child.path"
                >
                  <span class="submenu-title">{{ child.name }}</span>
                </el-menu-item>
              </el-sub-menu>
              
              <!-- 无子菜单 -->
              <el-menu-item v-else :index="item.path || `menu-${item.id}`">
                <div class="menu-item-content">
                  <el-icon v-if="item.icon" class="menu-icon"><component :is="item.icon" /></el-icon>
                  <span class="menu-title">{{ item.name }}</span>
                </div>
              </el-menu-item>
            </template>
          </el-menu>
        </el-scrollbar>
      </div>
      
      <!-- 折叠按钮 -->
      <div class="collapse-section">
        <div class="collapse-btn" @click="isCollapse = !isCollapse">
          <el-icon :size="18">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
        </div>
      </div>
    </el-aside>
    
    <el-container class="main-container">
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <!-- 面包屑 -->
          <div class="breadcrumb-wrapper">
            <el-icon class="breadcrumb-icon"><Location /></el-icon>
            <el-breadcrumb separator="/">
              <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
                {{ item.title }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
        </div>
        
        <div class="header-right">
          <!-- 快捷操作 -->
          <div class="header-actions">
            <!-- 搜索 -->
            <el-tooltip content="全局搜索" placement="bottom">
              <div class="action-btn" @click="showSearch = true">
                <el-icon :size="18"><Search /></el-icon>
              </div>
            </el-tooltip>
            
            <!-- 全屏 -->
            <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏'" placement="bottom">
              <div class="action-btn" @click="toggleFullscreen">
                <el-icon :size="18">
                  <FullScreen v-if="!isFullscreen" />
                  <ScaleToOriginal v-else />
                </el-icon>
              </div>
            </el-tooltip>
            
            <!-- 刷新 -->
            <el-tooltip content="刷新页面" placement="bottom">
              <div class="action-btn" @click="refreshPage">
                <el-icon :size="18"><Refresh /></el-icon>
              </div>
            </el-tooltip>
          </div>
          
          <!-- 分割线 -->
          <div class="header-divider"></div>
          
          <!-- 用户信息 -->
          <el-dropdown @command="handleCommand" trigger="click" placement="bottom-end">
            <div class="user-info">
              <el-avatar :size="36" class="user-avatar">
                {{ userStore.user?.real_name?.charAt(0) || userStore.user?.username?.charAt(0) || 'A' }}
              </el-avatar>
              <div class="user-detail">
                <span class="user-name">{{ userStore.user?.real_name || userStore.user?.username }}</span>
                <span class="user-role">{{ roleLabels[userStore.user?.role] || '用户' }}</span>
              </div>
              <el-icon class="dropdown-arrow"><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu class="user-dropdown-menu">
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人信息
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Key /></el-icon>
                  修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 主内容区 -->
      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="slide-fade" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" :key="route.path" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
      
      <!-- 页脚 -->
      <el-footer class="footer" height="40px">
        <span>OpsCenter © 2024</span>
        <span class="divider">|</span>
        <a href="https://github.com/AlexLiu-vibecoding/ops-management-platform" target="_blank">GitHub</a>
      </el-footer>
    </el-container>
    
    <!-- 全局搜索对话框 -->
    <el-dialog
      v-model="showSearch"
      title=""
      width="500px"
      class="search-dialog"
      :show-close="false"
    >
      <el-input
        v-model="searchKeyword"
        placeholder="搜索菜单、功能..."
        :prefix-icon="Search"
        size="large"
        clearable
        @keyup.enter="handleSearch"
      />
      <div v-if="searchResults.length > 0" class="search-results">
        <div 
          v-for="item in searchResults" 
          :key="item.path" 
          class="search-item"
          @click="navigateTo(item.path)"
        >
          <el-icon><component :is="item.icon" v-if="item.icon" /></el-icon>
          <span>{{ item.name }}</span>
        </div>
      </div>
    </el-dialog>
    
    <!-- 修改密码对话框 -->
    <el-dialog v-model="passwordDialog.visible" title="修改密码" width="420px" class="password-dialog">
      <el-form :model="passwordDialog.form" label-width="80px">
        <el-form-item label="原密码">
          <el-input
            v-model="passwordDialog.form.oldPassword"
            type="password"
            show-password
            placeholder="请输入原密码"
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="passwordDialog.form.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="passwordDialog.form.confirmPassword"
            type="password"
            show-password
            placeholder="请再次输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="changePassword">确定</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Coin, Fold, Expand, ArrowDown, Search, FullScreen, ScaleToOriginal,
  Refresh, Location, User, Key, SwitchButton
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const isFullscreen = ref(false)
const showSearch = ref(false)
const searchKeyword = ref('')
const dynamicMenus = ref([])
const cachedViews = ref(['Dashboard'])

// 角色标签映射
const roleLabels = {
  super_admin: '超级管理员',
  approval_admin: '审批管理员',
  operator: '运维人员',
  viewer: '只读用户'
}

// 活动菜单
const activeMenu = computed(() => route.path)

// 菜单弹出层样式
const menuPopperClass = computed(() => isCollapse.value ? 'menu-popper collapsed' : 'menu-popper')

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

// 搜索结果
const searchResults = computed(() => {
  if (!searchKeyword.value) return []
  
  const results = []
  const search = (items) => {
    items.forEach(item => {
      if (item.name?.toLowerCase().includes(searchKeyword.value.toLowerCase())) {
        if (item.path) results.push(item)
      }
      if (item.children) search(item.children)
    })
  }
  search(menuItems.value)
  return results.slice(0, 10)
})

// 获取动态菜单
const fetchUserMenu = async () => {
  try {
    const menus = await request.get('/menu/user-menu')
    dynamicMenus.value = menus
  } catch (error) {
    console.warn('获取动态菜单失败，使用默认配置:', error)
    dynamicMenus.value = []
  }
}

// 全屏切换
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
    isFullscreen.value = true
  } else {
    document.exitFullscreen()
    isFullscreen.value = false
  }
}

// 刷新页面
const refreshPage = () => {
  router.go(0)
}

// 搜索导航
const navigateTo = (path) => {
  router.push(path)
  showSearch.value = false
  searchKeyword.value = ''
}

// 处理搜索
const handleSearch = () => {
  if (searchResults.value.length > 0) {
    navigateTo(searchResults.value[0].path)
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
    case 'profile':
      ElMessage.info('个人信息功能开发中')
      break
    case 'password':
      passwordDialog.value.visible = true
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
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
    ElMessage.warning('请填写完整信息')
    return
  }
  
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  
  if (newPassword.length < 6) {
    ElMessage.warning('密码长度至少6位')
    return
  }
  
  try {
    await authApi.changePassword(oldPassword, newPassword)
    ElMessage.success('密码修改成功，请重新登录')
    passwordDialog.value.visible = false
    userStore.logout()
  } catch (error) {
    // 错误已在拦截器中处理
  }
}

// 监听全屏变化
watch(() => document.fullscreenElement, () => {
  isFullscreen.value = !!document.fullscreenElement
})

onMounted(() => {
  fetchUserMenu()
})
</script>

<style lang="scss" scoped>
// 变量定义
$primary-color: #6366f1;
$primary-light: #818cf8;
$sidebar-bg: linear-gradient(180deg, #1e1b4b 0%, #312e81 50%, #1e1b4b 100%);
$sidebar-width: 240px;
$sidebar-collapsed-width: 72px;

.main-layout {
  height: 100vh;
  overflow: hidden;
}

// 侧边栏样式
.aside {
  background: $sidebar-bg;
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  flex-direction: column;
  box-shadow: 4px 0 24px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 100;
  
  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
    pointer-events: none;
  }
}

// Logo区域
.logo-section {
  height: 72px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  position: relative;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  
  &.collapsed {
    justify-content: center;
    padding: 0;
  }
  
  .logo-icon {
    flex-shrink: 0;
    
    .logo-bg {
      width: 40px;
      height: 40px;
      border-radius: 12px;
      background: linear-gradient(135deg, $primary-color 0%, $primary-light 100%);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
    }
  }
  
  .logo-content {
    margin-left: 12px;
    display: flex;
    flex-direction: column;
    
    .logo-text {
      font-size: 18px;
      font-weight: 700;
      color: white;
      letter-spacing: 0.5px;
    }
    
    .logo-subtitle {
      font-size: 11px;
      color: rgba(255, 255, 255, 0.5);
      margin-top: 2px;
    }
  }
}

// 菜单区域
.menu-wrapper {
  flex: 1;
  overflow: hidden;
  
  :deep(.el-scrollbar__view) {
    padding: 8px 0;
  }
}

.aside-menu {
  border-right: none;
  background: transparent !important;
  
  :deep(.el-menu-item),
  :deep(.el-sub-menu__title) {
    height: 48px;
    line-height: 48px;
    margin: 4px 12px;
    border-radius: 10px;
    color: rgba(255, 255, 255, 0.7) !important;
    background: transparent !important;
    transition: all 0.2s ease;
    
    &:hover {
      background: rgba(255, 255, 255, 0.08) !important;
      color: white !important;
    }
  }
  
  :deep(.el-menu-item.is-active) {
    background: linear-gradient(135deg, $primary-color 0%, $primary-light 100%) !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    
    .menu-icon {
      color: white !important;
    }
  }
  
  :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
    color: white !important;
    
    .menu-icon {
      color: $primary-light !important;
    }
  }
  
  :deep(.el-icon) {
    color: rgba(255, 255, 255, 0.6);
  }
  
  // 子菜单项
  :deep(.el-menu--inline) {
    .el-menu-item {
      height: 42px;
      line-height: 42px;
      margin: 2px 12px;
      padding-left: 56px !important;
      
      &:hover {
        background: rgba(255, 255, 255, 0.05) !important;
      }
      
      &.is-active {
        background: rgba(99, 102, 241, 0.15) !important;
        color: $primary-light !important;
        box-shadow: none;
      }
    }
  }
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .menu-icon {
    font-size: 18px;
  }
  
  .menu-title {
    font-size: 14px;
    font-weight: 500;
  }
}

.submenu-title {
  font-size: 13px;
}

// 折叠按钮
.collapse-section {
  padding: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  
  .collapse-btn {
    width: 100%;
    height: 40px;
    border-radius: 10px;
    background: rgba(255, 255, 255, 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: rgba(255, 255, 255, 0.6);
    transition: all 0.2s ease;
    
    &:hover {
      background: rgba(255, 255, 255, 0.1);
      color: white;
    }
  }
}

// Logo过渡动画
.logo-fade-enter-active,
.logo-fade-leave-active {
  transition: opacity 0.2s ease;
}

.logo-fade-enter-from,
.logo-fade-leave-to {
  opacity: 0;
}

// 主容器
.main-container {
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}

// 顶部导航
.header {
  height: 60px;
  background: white;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  z-index: 99;
  
  .header-left {
    display: flex;
    align-items: center;
    
    .breadcrumb-wrapper {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .breadcrumb-icon {
        color: #909399;
      }
      
      :deep(.el-breadcrumb) {
        font-size: 13px;
        
        .el-breadcrumb__item {
          .el-breadcrumb__inner {
            color: #606266;
            font-weight: 400;
          }
          
          &:last-child .el-breadcrumb__inner {
            color: #303133;
            font-weight: 500;
          }
        }
      }
    }
  }
  
  .header-right {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .header-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      
      .action-btn {
        width: 36px;
        height: 36px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        color: #606266;
        transition: all 0.2s ease;
        
        &:hover {
          background: #f0f2f5;
          color: $primary-color;
        }
      }
    }
    
    .header-divider {
      width: 1px;
      height: 24px;
      background: #e4e7ed;
    }
    
    .user-info {
      display: flex;
      align-items: center;
      gap: 10px;
      cursor: pointer;
      padding: 6px 12px;
      border-radius: 10px;
      transition: all 0.2s ease;
      
      &:hover {
        background: #f5f7fa;
      }
      
      .user-avatar {
        background: linear-gradient(135deg, $primary-color 0%, $primary-light 100%);
        color: white;
        font-weight: 600;
        font-size: 14px;
      }
      
      .user-detail {
        display: flex;
        flex-direction: column;
        
        .user-name {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
        }
        
        .user-role {
          font-size: 11px;
          color: #909399;
        }
      }
      
      .dropdown-arrow {
        color: #909399;
        font-size: 12px;
        transition: transform 0.2s ease;
      }
    }
  }
}

// 主内容区
.main {
  flex: 1;
  padding: 20px;
  overflow: auto;
  
  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }
  
  &::-webkit-scrollbar-thumb {
    background: #c0c4cc;
    border-radius: 3px;
    
    &:hover {
      background: #909399;
    }
  }
}

// 页脚
.footer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: white;
  border-top: 1px solid #f0f2f5;
  font-size: 12px;
  color: #909399;
  
  .divider {
    color: #dcdfe6;
  }
  
  a {
    color: #909399;
    text-decoration: none;
    
    &:hover {
      color: $primary-color;
    }
  }
}

// 页面过渡动画
.slide-fade-enter-active {
  transition: all 0.25s ease-out;
}

.slide-fade-leave-active {
  transition: all 0.2s ease-in;
}

.slide-fade-enter-from {
  transform: translateX(20px);
  opacity: 0;
}

.slide-fade-leave-to {
  transform: translateX(-20px);
  opacity: 0;
}
</style>

<style lang="scss">
// 全局样式 - 菜单弹出层
.menu-popper {
  background: #1e1b4b !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  border-radius: 12px !important;
  padding: 8px !important;
  
  &.collapsed {
    .el-menu-item {
      height: 42px;
      line-height: 42px;
      margin: 2px 4px;
      border-radius: 8px;
      color: rgba(255, 255, 255, 0.7) !important;
      background: transparent !important;
      
      &:hover {
        background: rgba(255, 255, 255, 0.08) !important;
        color: white !important;
      }
      
      &.is-active {
        background: linear-gradient(135deg, #6366f1 0%, #818cf8 100%) !important;
        color: white !important;
      }
    }
  }
}

// 用户下拉菜单
.user-dropdown-menu {
  margin-top: 8px;
  border-radius: 12px;
  padding: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  
  .el-dropdown-menu__item {
    border-radius: 8px;
    padding: 10px 16px;
    display: flex;
    align-items: center;
    gap: 10px;
    
    &:hover {
      background: #f5f7fa;
      color: #6366f1;
    }
  }
}

// 搜索对话框
.search-dialog {
  .el-dialog__header {
    display: none;
  }
  
  .el-dialog__body {
    padding: 20px;
  }
  
  .search-results {
    margin-top: 16px;
    max-height: 300px;
    overflow-y: auto;
    
    .search-item {
      padding: 12px 16px;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 12px;
      
      &:hover {
        background: #f5f7fa;
      }
    }
  }
}

// 密码对话框
.password-dialog {
  .el-dialog__body {
    padding: 24px;
  }
}
</style>
