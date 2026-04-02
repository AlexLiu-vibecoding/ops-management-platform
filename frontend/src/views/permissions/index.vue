<template>
  <div class="permissions-page">
    <el-row :gutter="20">
      <!-- 左侧角色列表 -->
      <el-col :span="6">
        <el-card shadow="never" class="role-card">
          <template #header>
            <div class="card-header">
              <span>角色管理</span>
            </div>
          </template>
          
          <div class="role-list">
            <div
              v-for="role in roles"
              :key="role.role"
              :class="['role-item', { active: selectedRole === role.role }]"
              @click="selectRole(role.role)"
            >
              <div class="role-info">
                <div class="role-header">
                  <span class="role-name">{{ role.name }}</span>
                  <el-tag size="small" :color="role.color" style="border: none; margin-left: 8px;">
                    {{ role.user_count }} 人
                  </el-tag>
                </div>
                <div class="role-desc">{{ role.description }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧角色详情 -->
      <el-col :span="18">
        <el-card shadow="never" class="detail-card" v-loading="detailLoading">
          <template #header>
            <div class="card-header">
              <div class="header-title">
                <span>{{ currentRoleName }}</span>
                <el-tag :color="currentRoleColor" style="border: none; margin-left: 8px;">
                  {{ selectedRole }}
                </el-tag>
              </div>
            </div>
          </template>
          
          <el-tabs v-model="activeTab" class="detail-tabs">
            <!-- 环境权限 Tab -->
            <el-tab-pane label="环境权限" name="environments">
              <div class="tab-content">
                <div class="section-header">
                  <span class="section-title">可访问的环境</span>
                  <span class="section-tip">用户将继承所属角色的环境权限</span>
                </div>
                <div class="environment-grid">
                  <div
                    v-for="env in allEnvironments"
                    :key="env.id"
                    :class="['env-item', { selected: selectedEnvIds.includes(env.id) }]"
                    @click="toggleEnvironment(env.id)"
                  >
                    <div class="env-checkbox">
                      <el-icon v-if="selectedEnvIds.includes(env.id)" color="#409eff">
                        <Select />
                      </el-icon>
                    </div>
                    <div class="env-info">
                      <div class="env-name">{{ env.name }}</div>
                      <div class="env-code">{{ env.code }}</div>
                    </div>
                    <div class="env-color" :style="{ backgroundColor: env.color }"></div>
                  </div>
                </div>
              </div>
            </el-tab-pane>
            
            <!-- 功能权限 Tab -->
            <el-tab-pane label="功能权限" name="permissions">
              <div class="tab-content">
                <div class="section-header">
                  <span class="section-title">功能权限配置</span>
                  <div class="section-actions">
                    <el-button size="small" @click="handleExpandAll">展开全部</el-button>
                    <el-button size="small" @click="handleCollapseAll">收起全部</el-button>
                  </div>
                </div>
                <div class="permission-tree-container">
                  <el-tree
                    ref="treeRef"
                    :data="permissionTree"
                    :props="treeProps"
                    show-checkbox
                    node-key="id"
                    :default-expand-all="false"
                    :default-expanded-keys="expandedKeys"
                    @check="handlePermissionCheck"
                  >
                    <template #default="{ node, data }">
                      <div class="tree-node">
                        <span class="node-name">{{ data.name }}</span>
                        <el-tag v-if="data.module" size="small" type="info" class="node-module">
                          {{ getModuleName(data.module) }}
                        </el-tag>
                        <el-tag v-if="data.category" size="small" :type="getCategoryType(data.category)">
                          {{ getCategoryName(data.category) }}
                        </el-tag>
                      </div>
                    </template>
                  </el-tree>
                </div>
              </div>
            </el-tab-pane>
            
            <!-- 用户列表 Tab -->
            <el-tab-pane label="用户列表" name="users">
              <div class="tab-content">
                <div class="section-header">
                  <span class="section-title">该角色下的用户</span>
                  <div class="section-actions">
                    <el-button type="primary" size="small" @click="openAddUserDialog">
                      <el-icon><Plus /></el-icon>
                      添加用户
                    </el-button>
                  </div>
                </div>
                <el-table :data="roleUsers" stripe style="width: 100%">
                  <el-table-column prop="username" label="用户名" width="150" />
                  <el-table-column prop="real_name" label="姓名" width="120" />
                  <el-table-column prop="email" label="邮箱" />
                  <el-table-column prop="status" label="状态" min-width="80">
                    <template #default="{ row }">
                      <el-tag :type="row.status ? 'success' : 'danger'" size="small">
                        {{ row.status ? '正常' : '禁用' }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="last_login_time" label="最后登录" width="180">
                    <template #default="{ row }">
                      {{ formatTime(row.last_login_time) }}
                    </template>
                  </el-table-column>
                  <el-table-column label="操作" min-width="80" fixed="right" align="center">
                    <template #default="{ row }">
                      <TableActions :row="row" :actions="userActions" @remove="handleRemoveUser" />
                    </template>
                  </el-table-column>
                </el-table>
              </div>
            </el-tab-pane>
          </el-tabs>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 添加用户对话框 -->
    <el-dialog 
      v-model="addUserDialogVisible" 
      title="添加用户到角色" 
      width="600px"
      @close="closeAddUserDialog"
    >
      <div class="add-user-dialog">
        <!-- 搜索框 -->
        <el-input
          v-model="userSearchKeyword"
          placeholder="搜索用户名、姓名或邮箱"
          clearable
          @keyup.enter="searchAvailableUsers"
          @clear="searchAvailableUsers"
          class="search-input"
        >
          <template #append>
            <el-button @click="searchAvailableUsers">搜索</el-button>
          </template>
        </el-input>
        
        <!-- 用户列表 -->
        <div class="user-list-container" v-loading="userListLoading">
          <div v-if="availableUsers.length === 0" class="empty-tip">
            暂无可添加的用户
          </div>
          <el-checkbox-group v-else v-model="selectedUserIds" class="user-checkbox-group">
            <div 
              v-for="user in availableUsers" 
              :key="user.id" 
              class="user-item"
            >
              <el-checkbox :value="user.id">
                <div class="user-info">
                  <span class="username">{{ user.username }}</span>
                  <span class="real-name" v-if="user.real_name">({{ user.real_name }})</span>
                  <el-tag 
                    v-if="user.role" 
                    size="small" 
                    type="info"
                    class="current-role"
                  >
                    {{ getRoleName(user.role) }}
                  </el-tag>
                </div>
                <div class="user-email" v-if="user.email">{{ user.email }}</div>
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </div>
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addUserDialogVisible = false">取消</el-button>
          <el-button 
            type="primary" 
            :disabled="selectedUserIds.length === 0"
            :loading="addUserLoading"
            @click="handleAddUsers"
          >
            添加 ({{ selectedUserIds.length }})
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Select, Plus } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

// 操作列配置
const userActions = computed(() => [
  { 
    key: 'remove', 
    label: '移除', 
    event: 'remove', 
    danger: true, 
    primary: true,
    visible: (row) => row.id !== currentUserId.value
  }
])

// 角色列表
const roles = ref([])
const selectedRole = ref('')
const detailLoading = ref(false)

// 详情数据
const activeTab = ref('environments')
const allEnvironments = ref([])
const selectedEnvIds = ref([])
const roleUsers = ref([])
const permissionTree = ref([])
const expandedKeys = ref([])

const treeRef = ref(null)
const treeProps = {
  children: 'children',
  label: 'name'
}

// 添加用户对话框
const addUserDialogVisible = ref(false)
const userSearchKeyword = ref('')
const availableUsers = ref([])
const selectedUserIds = ref([])
const userListLoading = ref(false)
const addUserLoading = ref(false)

// 模块名称映射
const moduleNames = {
  instance: '实例管理',
  environment: '环境管理',
  approval: '变更管理',
  monitor: '监控管理',
  script: '脚本管理',
  system: '系统管理',
  notification: '通知管理',
  audit: '审计管理',
  scheduled_task: '定时任务',
  ai: 'AI配置'
}

const getModuleName = (module) => moduleNames[module] || module

// 类别映射
const categoryMap = {
  menu: { name: '菜单', type: 'primary' },
  button: { name: '按钮', type: 'success' },
  api: { name: '接口', type: 'warning' }
}

const getCategoryName = (category) => categoryMap[category]?.name || category
const getCategoryType = (category) => categoryMap[category]?.type || 'info'

// 角色名称映射
const roleNames = {
  super_admin: '超级管理员',
  approval_admin: '审批管理员',
  operator: '运维人员',
  developer: '开发人员',
  readonly: '只读用户'
}

const getRoleName = (role) => roleNames[role] || role

// 当前角色信息
const currentRoleName = computed(() => {
  const role = roles.value.find(r => r.role === selectedRole.value)
  return role?.name || ''
})

const currentRoleColor = computed(() => {
  const role = roles.value.find(r => r.role === selectedRole.value)
  return role?.color || '#909399'
})

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// 获取角色列表
const fetchRoles = async () => {
  try {
    const data = await request.get('/permissions/roles')
    roles.value = data.items || []
    if (roles.value.length > 0 && !selectedRole.value) {
      selectRole(roles.value[0].role)
    }
  } catch (error) {
    console.error('获取角色列表失败:', error)
    ElMessage.error('获取角色列表失败')
  }
}

// 获取角色详情
const fetchRoleDetail = async (role) => {
  detailLoading.value = true
  try {
    const data = await request.get(`/permissions/roles/${role}`)
    
    // 设置环境权限
    selectedEnvIds.value = data.environment_ids || []
    
    // 设置用户列表
    roleUsers.value = data.users || []
    
    // 设置功能权限
    await nextTick()
    if (treeRef.value) {
      treeRef.value.setCheckedKeys(data.permission_ids || [])
    }
    
  } catch (error) {
    console.error('获取角色详情失败:', error)
    ElMessage.error('获取角色详情失败')
  } finally {
    detailLoading.value = false
  }
}

// 获取所有环境
const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    allEnvironments.value = (data.items || []).filter(e => e.status)
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

// 获取权限树
const fetchPermissions = async () => {
  try {
    const data = await request.get('/permissions')
    permissionTree.value = data.items || []
    expandedKeys.value = permissionTree.value.map(item => item.id)
  } catch (error) {
    console.error('获取权限树失败:', error)
  }
}

// 选择角色
const selectRole = (role) => {
  selectedRole.value = role
  fetchRoleDetail(role)
}

// 切换环境选择
const toggleEnvironment = async (envId) => {
  const index = selectedEnvIds.value.indexOf(envId)
  if (index === -1) {
    selectedEnvIds.value.push(envId)
  } else {
    selectedEnvIds.value.splice(index, 1)
  }
  
  // 自动保存环境权限
  await saveEnvironmentPermissions()
}

// 保存环境权限
const saveEnvironmentPermissions = async () => {
  if (!selectedRole.value) return
  
  try {
    await request.put(`/permissions/roles/${selectedRole.value}/environments`, {
      environment_ids: selectedEnvIds.value
    })
    ElMessage.success('环境权限已保存')
    fetchRoles() // 刷新角色列表
  } catch (error) {
    console.error('保存环境权限失败:', error)
    ElMessage.error('保存环境权限失败')
  }
}

// 权限树勾选变化时自动保存
const handlePermissionCheck = async () => {
  if (!selectedRole.value || !treeRef.value) return
  
  const checkedIds = treeRef.value.getCheckedKeys()
  const halfCheckedIds = treeRef.value.getHalfCheckedKeys()
  const allIds = [...checkedIds, ...halfCheckedIds]
  
  try {
    await request.put(`/permissions/roles/${selectedRole.value}/permissions`, {
      role: selectedRole.value,
      permission_ids: allIds
    })
    ElMessage.success('功能权限已保存')
    fetchRoles() // 刷新角色列表
  } catch (error) {
    console.error('保存功能权限失败:', error)
    ElMessage.error('保存功能权限失败')
    // 刷新恢复原状态
    fetchRoleDetail(selectedRole.value)
  }
}

// 展开全部
const handleExpandAll = () => {
  if (!treeRef.value) return
  Object.keys(treeRef.value.store.nodesMap).forEach(key => {
    treeRef.value.store.nodesMap[key].expanded = true
  })
}

// 收起全部
const handleCollapseAll = () => {
  if (!treeRef.value) return
  Object.keys(treeRef.value.store.nodesMap).forEach(key => {
    treeRef.value.store.nodesMap[key].expanded = false
  })
}

// 打开添加用户对话框
const openAddUserDialog = async () => {
  addUserDialogVisible.value = true
  userSearchKeyword.value = ''
  selectedUserIds.value = []
  await searchAvailableUsers()
}

// 关闭添加用户对话框
const closeAddUserDialog = () => {
  addUserDialogVisible.value = false
  userSearchKeyword.value = ''
  selectedUserIds.value = []
  availableUsers.value = []
}

// 搜索可添加的用户
const searchAvailableUsers = async () => {
  userListLoading.value = true
  try {
    const params = {}
    if (userSearchKeyword.value) {
      params.search = userSearchKeyword.value
    }
    const data = await request.get(`/permissions/roles/${selectedRole.value}/available-users`, { params })
    availableUsers.value = data.items || []
  } catch (error) {
    console.error('获取可用用户列表失败:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    userListLoading.value = false
  }
}

// 添加用户到角色
const handleAddUsers = async () => {
  if (selectedUserIds.value.length === 0) {
    ElMessage.warning('请选择要添加的用户')
    return
  }
  
  addUserLoading.value = true
  try {
    const data = await request.post(`/permissions/roles/${selectedRole.value}/users`, {
      user_ids: selectedUserIds.value
    })
    
    ElMessage.success(data.message || '添加成功')
    addUserDialogVisible.value = false
    
    // 刷新角色详情和列表
    fetchRoleDetail(selectedRole.value)
    fetchRoles()
  } catch (error) {
    console.error('添加用户失败:', error)
    ElMessage.error('添加用户失败')
  } finally {
    addUserLoading.value = false
  }
}

// 从角色移除用户
const handleRemoveUser = async (user) => {
  try {
    await ElMessageBox.confirm(
      `确定要将用户 "${user.username}" 从角色 "${currentRoleName.value}" 中移除吗？移除后用户将变为只读用户。`,
      '确认移除',
      { type: 'warning' }
    )
    
    await request.delete(`/permissions/roles/${selectedRole.value}/users/${user.id}`)
    
    ElMessage.success('移除成功')
    
    // 刷新角色详情和列表
    fetchRoleDetail(selectedRole.value)
    fetchRoles()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('移除用户失败:', error)
      ElMessage.error('移除用户失败')
    }
  }
}

onMounted(() => {
  fetchRoles()
  fetchEnvironments()
  fetchPermissions()
})
</script>

<style lang="scss" scoped>
.permissions-page {
  .role-card {
    height: calc(100vh - 180px);
    
    :deep(.el-card__body) {
      padding: 0;
      height: calc(100% - 56px);
      overflow-y: auto;
    }
  }
  
  .detail-card {
    height: calc(100vh - 180px);
    
    :deep(.el-card__body) {
      padding: 0;
      height: calc(100% - 56px);
      display: flex;
      flex-direction: column;
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-title {
      display: flex;
      align-items: center;
      font-size: 16px;
      font-weight: 500;
    }
  }
  
  .role-list {
    .role-item {
      padding: 16px;
      border-bottom: 1px solid var(--el-border-color-lighter);
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        background-color: var(--el-fill-color-light);
      }
      
      &.active {
        background-color: var(--el-color-primary-light-9);
        border-left: 3px solid var(--el-color-primary);
      }
      
      .role-info {
        .role-header {
          display: flex;
          align-items: center;
          margin-bottom: 8px;
        }
        
        .role-name {
          font-weight: 600;
          font-size: 15px;
        }
        
        .role-desc {
          font-size: 13px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
  
  .detail-tabs {
    flex: 1;
    display: flex;
    flex-direction: column;
    
    :deep(.el-tabs__content) {
      flex: 1;
      overflow-y: auto;
    }
    
    :deep(.el-tab-pane) {
      height: 100%;
    }
  }
  
  .tab-content {
    padding: 16px;
    height: 100%;
    overflow-y: auto;
  }
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    .section-title {
      font-weight: 500;
      font-size: 15px;
    }
    
    .section-tip {
      font-size: 13px;
      color: var(--el-text-color-secondary);
    }
    
    .section-actions {
      display: flex;
      gap: 8px;
    }
  }
  
  .environment-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    
    .env-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      border: 1px solid var(--el-border-color);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        border-color: var(--el-color-primary-light-5);
        background-color: var(--el-fill-color-light);
      }
      
      &.selected {
        border-color: var(--el-color-primary);
        background-color: var(--el-color-primary-light-9);
      }
      
      .env-checkbox {
        width: 20px;
        height: 20px;
        border: 1px solid var(--el-border-color);
        border-radius: 4px;
        margin-right: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      
      &.selected .env-checkbox {
        border-color: var(--el-color-primary);
        background-color: var(--el-color-primary-light-8);
      }
      
      .env-info {
        flex: 1;
        
        .env-name {
          font-weight: 500;
          margin-bottom: 2px;
        }
        
        .env-code {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
      
      .env-color {
        width: 4px;
        height: 40px;
        border-radius: 2px;
      }
    }
  }
  
  .permission-tree-container {
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 8px;
    padding: 16px;
    max-height: 500px;
    overflow-y: auto;
    
    .tree-node {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .node-name {
        font-weight: 500;
      }
      
      .node-module {
        margin-left: 8px;
      }
    }
  }
  
  .add-user-dialog {
    .search-input {
      margin-bottom: 16px;
    }
    
    .user-list-container {
      max-height: 400px;
      overflow-y: auto;
      border: 1px solid var(--el-border-color-lighter);
      border-radius: 8px;
      padding: 12px;
      
      .empty-tip {
        text-align: center;
        color: var(--el-text-color-secondary);
        padding: 20px;
      }
      
      .user-checkbox-group {
        display: flex;
        flex-direction: column;
        gap: 8px;
        
        .user-item {
          padding: 12px;
          border-radius: 6px;
          transition: background-color 0.2s;
          
          &:hover {
            background-color: var(--el-fill-color-light);
          }
          
          :deep(.el-checkbox) {
            width: 100%;
            align-items: flex-start;
            
            .el-checkbox__label {
              flex: 1;
            }
          }
          
          .user-info {
            display: flex;
            align-items: center;
            gap: 8px;
            
            .username {
              font-weight: 500;
            }
            
            .real-name {
              color: var(--el-text-color-secondary);
              font-size: 13px;
            }
            
            .current-role {
              margin-left: auto;
            }
          }
          
          .user-email {
            margin-top: 4px;
            font-size: 12px;
            color: var(--el-text-color-secondary);
            padding-left: 0;
          }
        }
      }
    }
  }
}
</style>
