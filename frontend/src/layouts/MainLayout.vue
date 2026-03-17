<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapse ? '64px' : '220px'" class="aside">
      <div class="logo">
        <el-icon :size="24"><Coin /></el-icon>
        <span v-if="!isCollapse" class="logo-text">MySQL管理平台</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapse"
        :router="true"
        class="aside-menu"
        background-color="#1d1e1f"
        text-color="rgba(255, 255, 255, 0.85)"
        active-text-color="#409eff"
      >
        <template v-for="item in menuItems" :key="item.path || item.id">
          <!-- 有子菜单 -->
          <el-sub-menu v-if="item.children && item.children.length > 0" :index="item.path || `menu-${item.id}`">
            <template #title>
              <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
              <span>{{ item.name }}</span>
            </template>
            <el-menu-item
              v-for="child in item.children"
              :key="child.path"
              :index="child.path"
            >
              {{ child.name }}
            </el-menu-item>
          </el-sub-menu>
          
          <!-- 无子菜单 -->
          <el-menu-item v-else :index="item.path || `menu-${item.id}`">
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
            <template #title>{{ item.name }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    
    <el-container>
      <!-- 头部 -->
      <el-header class="header">
        <div class="header-left">
          <el-icon
            class="collapse-btn"
            :size="20"
            @click="isCollapse = !isCollapse"
          >
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          
          <el-breadcrumb separator="/">
            <el-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ userStore.user?.real_name || userStore.user?.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
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
    <el-dialog v-model="passwordDialog.visible" title="修改密码" width="400px">
      <el-form :model="passwordDialog.form" label-width="80px">
        <el-form-item label="原密码">
          <el-input
            v-model="passwordDialog.form.oldPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input
            v-model="passwordDialog.form.newPassword"
            type="password"
            show-password
          />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input
            v-model="passwordDialog.form.confirmPassword"
            type="password"
            show-password
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { authApi } from '@/api/auth'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UserFilled, Fold, Expand, ArrowDown } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isCollapse = ref(false)
const dynamicMenus = ref([])

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

// 菜单项（优先使用后端配置，兜底使用路由配置）
const menuItems = computed(() => {
  if (dynamicMenus.value.length > 0) {
    return dynamicMenus.value
  }
  
  // 兜底：使用路由配置
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
    // 如果获取失败，使用路由配置兜底
    console.warn('获取动态菜单失败，使用默认配置:', error)
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
    case 'profile':
      // TODO: 跳转到个人信息页面
      break
    case 'password':
      passwordDialog.value.visible = true
      break
    case 'logout':
      ElMessageBox.confirm('确定要退出登录吗？', '提示', {
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
    ElMessage.warning('请填写完整信息')
    return
  }
  
  if (newPassword !== confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
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

onMounted(() => {
  fetchUserMenu()
})
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
}

.aside {
  background-color: #1d1e1f;
  transition: width 0.3s;
  overflow: hidden;
  
  .logo {
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #fff;
    font-size: 18px;
    font-weight: bold;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    
    .logo-text {
      margin-left: 10px;
      white-space: nowrap;
    }
  }
  
  .aside-menu {
    border-right: none;
    
    // 确保菜单文字清晰可见
    :deep(.el-menu-item),
    :deep(.el-sub-menu__title) {
      color: rgba(255, 255, 255, 0.85) !important;
      
      &:hover {
        background-color: rgba(255, 255, 255, 0.08) !important;
      }
    }
    
    :deep(.el-menu-item.is-active) {
      color: #409eff !important;
      background-color: rgba(64, 158, 255, 0.1) !important;
    }
    
    :deep(.el-sub-menu.is-active > .el-sub-menu__title) {
      color: #409eff !important;
    }
    
    :deep(.el-icon) {
      color: rgba(255, 255, 255, 0.85);
    }
  }
}

.header {
  background: #fff;
  box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  
  .header-left {
    display: flex;
    align-items: center;
    
    .collapse-btn {
      cursor: pointer;
      margin-right: 20px;
      
      &:hover {
        color: #1890ff;
      }
    }
  }
  
  .header-right {
    .user-dropdown {
      display: flex;
      align-items: center;
      cursor: pointer;
      
      .username {
        margin: 0 8px;
      }
    }
  }
}

.main {
  background: #f0f2f5;
  padding: 20px;
  overflow: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
