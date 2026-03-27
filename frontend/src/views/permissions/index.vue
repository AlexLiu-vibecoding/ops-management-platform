<template>
  <div class="permissions-page">
    <el-row :gutter="20">
      <!-- 左侧角色列表 -->
      <el-col :span="6">
        <el-card shadow="never" class="role-card">
          <template #header>
            <div class="card-header">
              <span>角色列表</span>
              <el-button type="primary" size="small" @click="handleResetDefault" :loading="resetLoading">
                重置默认
              </el-button>
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
                <div class="role-name">{{ role.name }}</div>
                <div class="role-desc">{{ role.description }}</div>
              </div>
              <el-tag size="small" type="info">{{ role.permission_count }} 项权限</el-tag>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧权限树 -->
      <el-col :span="18">
        <el-card shadow="never" class="permission-card">
          <template #header>
            <div class="card-header">
              <span>{{ currentRoleName }} - 权限配置</span>
              <div class="header-actions">
                <el-button @click="handleExpandAll">展开全部</el-button>
                <el-button @click="handleCollapseAll">收起全部</el-button>
                <el-button type="primary" @click="handleSave" :loading="saveLoading">
                  保存配置
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="permission-tree-container" v-loading="treeLoading">
            <el-tree
              ref="treeRef"
              :data="permissionTree"
              :props="treeProps"
              show-checkbox
              node-key="id"
              :default-expand-all="false"
              :default-expanded-keys="expandedKeys"
              :default-checked-keys="checkedKeys"
              @check="handleCheck"
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
                  <span class="node-code">{{ data.code }}</span>
                </div>
              </template>
            </el-tree>
          </div>
          
          <!-- 统计信息 -->
          <div class="permission-stats">
            <el-statistic title="已选权限" :value="checkedCount" />
            <el-statistic title="总权限数" :value="totalPermissions" />
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'

// 角色列表
const roles = ref([])
const selectedRole = ref('')
const resetLoading = ref(false)
const saveLoading = ref(false)
const treeLoading = ref(false)

// 权限树
const treeRef = ref(null)
const permissionTree = ref([])
const checkedKeys = ref([])
const expandedKeys = ref([])

const treeProps = {
  children: 'children',
  label: 'name'
}

// 模块名称映射
const moduleNames = {
  instance: '实例管理',
  environment: '环境管理',
  approval: '变更管理',
  monitor: '监控管理',
  script: '脚本管理',
  system: '系统管理'
}

// 获取模块名称
const getModuleName = (module) => {
  return moduleNames[module] || module
}

// 类别名称和类型映射
const categoryMap = {
  menu: { name: '菜单', type: 'primary' },
  button: { name: '按钮', type: 'success' },
  api: { name: '接口', type: 'warning' }
}

const getCategoryName = (category) => {
  return categoryMap[category]?.name || category
}

const getCategoryType = (category) => {
  return categoryMap[category]?.type || 'info'
}

// 当前角色名称
const currentRoleName = computed(() => {
  const role = roles.value.find(r => r.role === selectedRole.value)
  return role?.name || ''
})

// 已选权限数
const checkedCount = computed(() => {
  return checkedKeys.value.length
})

// 总权限数
const totalPermissions = computed(() => {
  let count = 0
  const countNodes = (nodes) => {
    nodes.forEach(node => {
      count++
      if (node.children?.length) {
        countNodes(node.children)
      }
    })
  }
  countNodes(permissionTree.value)
  return count
})

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

// 获取权限树
const fetchPermissions = async () => {
  treeLoading.value = true
  try {
    const data = await request.get('/permissions')
    permissionTree.value = data.items || []
    // 默认展开第一级
    expandedKeys.value = permissionTree.value.map(item => item.id)
  } catch (error) {
    console.error('获取权限树失败:', error)
    ElMessage.error('获取权限树失败')
  } finally {
    treeLoading.value = false
  }
}

// 获取角色权限
const fetchRolePermissions = async (role) => {
  try {
    const data = await request.get(`/permissions/roles/${role}/permissions`)
    checkedKeys.value = data.permission_ids || []
    // 等待树渲染完成后设置选中状态
    await nextTick()
    if (treeRef.value) {
      treeRef.value.setCheckedKeys(checkedKeys.value)
    }
  } catch (error) {
    console.error('获取角色权限失败:', error)
  }
}

// 选择角色
const selectRole = (role) => {
  selectedRole.value = role
  fetchRolePermissions(role)
}

// 处理选中变化
const handleCheck = (data, { checkedKeys }) => {
  checkedKeys.value = checkedKeys
}

// 展开全部
const handleExpandAll = () => {
  if (!treeRef.value) return
  const allKeys = []
  const collectKeys = (nodes) => {
    nodes.forEach(node => {
      allKeys.push(node.id)
      if (node.children?.length) {
        collectKeys(node.children)
      }
    })
  }
  collectKeys(permissionTree.value)
  
  // 展开所有节点
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

// 保存权限配置
const handleSave = async () => {
  if (!selectedRole.value) {
    ElMessage.warning('请先选择角色')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要保存 ${currentRoleName.value} 的权限配置吗？`,
      '确认保存',
      { type: 'warning' }
    )
    
    saveLoading.value = true
    // 获取选中的权限ID（包含半选的父节点）
    const checkedIds = treeRef.value.getCheckedKeys()
    const halfCheckedIds = treeRef.value.getHalfCheckedKeys()
    const allIds = [...checkedIds, ...halfCheckedIds]
    
    await request.put(`/permissions/roles/${selectedRole.value}/permissions`, {
      role: selectedRole.value,
      permission_ids: allIds
    })
    
    ElMessage.success('保存成功')
    fetchRoles() // 刷新角色列表以更新权限数量
  } catch (error) {
    if (error !== 'cancel') {
      console.error('保存失败:', error)
      ElMessage.error('保存失败')
    }
  } finally {
    saveLoading.value = false
  }
}

// 重置默认权限
const handleResetDefault = async () => {
  try {
    await ElMessageBox.confirm(
      '重置后所有角色将恢复为系统默认权限配置，确定要重置吗？',
      '重置确认',
      { type: 'warning' }
    )
    
    resetLoading.value = true
    await request.post('/permissions/roles/reset-default')
    ElMessage.success('重置成功')
    
    // 刷新数据
    await fetchRoles()
    if (selectedRole.value) {
      fetchRolePermissions(selectedRole.value)
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重置失败:', error)
      ElMessage.error('重置失败')
    }
  } finally {
    resetLoading.value = false
  }
}

onMounted(() => {
  fetchRoles()
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
  
  .permission-card {
    height: calc(100vh - 180px);
    
    :deep(.el-card__body) {
      height: calc(100% - 56px);
      display: flex;
      flex-direction: column;
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 8px;
    }
  }
  
  .role-list {
    .role-item {
      padding: 12px 16px;
      border-bottom: 1px solid var(--el-border-color-lighter);
      cursor: pointer;
      transition: all 0.3s;
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      &:hover {
        background-color: var(--el-fill-color-light);
      }
      
      &.active {
        background-color: var(--el-color-primary-light-9);
        border-left: 3px solid var(--el-color-primary);
      }
      
      .role-info {
        .role-name {
          font-weight: 500;
          margin-bottom: 4px;
        }
        
        .role-desc {
          font-size: 12px;
          color: var(--el-text-color-secondary);
        }
      }
    }
  }
  
  .permission-tree-container {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    
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
      
      .node-code {
        margin-left: auto;
        font-size: 12px;
        color: var(--el-text-color-secondary);
        font-family: monospace;
      }
    }
  }
  
  .permission-stats {
    display: flex;
    justify-content: flex-end;
    gap: 40px;
    padding: 16px;
    border-top: 1px solid var(--el-border-color-lighter);
    background-color: var(--el-fill-color-light);
  }
}
</style>
