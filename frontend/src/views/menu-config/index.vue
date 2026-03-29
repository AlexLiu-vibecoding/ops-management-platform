<template>
  <div class="menu-config-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>菜单配置</span>
          <div class="header-actions">
            <el-button type="success" @click="initDefaultMenus" :disabled="hasMenus">
              <el-icon><RefreshRight /></el-icon>
              初始化默认菜单
            </el-button>
            <el-button type="primary" @click="handleAdd(null)">
              <el-icon><Plus /></el-icon>
              添加菜单
            </el-button>
          </div>
        </div>
      </template>
      
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 15px;"
      >
        <template #title>
          配置系统导航菜单。可设置菜单名称、图标、路径、可见角色等。修改后刷新页面生效。
        </template>
      </el-alert>
      
      <el-table
        :data="menuList"
        style="width: 100%"
        row-key="id"
        default-expand-all
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        v-loading="loading"
      >
        <el-table-column prop="name" label="菜单名称" min-width="100" />
        <el-table-column prop="icon" label="图标" width="70" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.icon" :size="18"><component :is="row.icon" /></el-icon>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="path" label="路径" min-width="100">
          <template #default="{ row }">
            {{ row.path || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="60" align="center" />
        <el-table-column prop="is_visible" label="显示" width="60" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_visible ? 'success' : 'info'" size="small">
              {{ row.is_visible ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="启用" width="60" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="roles" label="可见角色" min-width="120">
          <template #default="{ row }">
            <template v-if="row.roles">
              <el-tag
                v-for="role in row.roles.split(',')"
                :key="role"
                size="small"
                style="margin-right: 4px;"
              >
                {{ getRoleLabel(role.trim()) }}
              </el-tag>
            </template>
            <span v-else>所有用户</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleAdd(row)">添加</el-button>
              <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 编辑对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑菜单' : '添加菜单'"
      width="550px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="dialog.form"
        :rules="dialog.rules"
        label-width="100px"
      >
        <el-form-item label="父级菜单">
          <el-cascader
            v-model="dialog.form.parent_id_path"
            :options="parentOptions"
            :props="{ checkStrictly: true, value: 'id', label: 'name', emitPath: false }"
            clearable
            placeholder="选择父级菜单（可选）"
            style="width: 100%;"
          />
        </el-form-item>
        
        <el-form-item label="菜单名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入菜单名称" />
        </el-form-item>
        
        <el-form-item label="路由路径" prop="path">
          <el-input v-model="dialog.form.path" placeholder="如 /dashboard" />
        </el-form-item>
        
        <el-form-item label="图标">
          <el-select
            v-model="dialog.form.icon"
            placeholder="选择图标"
            filterable
            clearable
            style="width: 100%;"
          >
            <el-option
              v-for="icon in iconOptions"
              :key="icon"
              :label="icon"
              :value="icon"
            >
              <el-icon style="margin-right: 8px;"><component :is="icon" /></el-icon>
              <span>{{ icon }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        
        <el-form-item label="排序">
          <el-input-number v-model="dialog.form.sort_order" :min="0" :max="999" />
        </el-form-item>
        
        <el-form-item label="是否显示">
          <el-switch v-model="dialog.form.is_visible" />
        </el-form-item>
        
        <el-form-item label="是否启用">
          <el-switch v-model="dialog.form.is_enabled" />
        </el-form-item>
        
        <el-form-item label="可见角色">
          <el-select
            v-model="dialog.form.roleList"
            multiple
            placeholder="不选则所有用户可见"
            style="width: 100%;"
          >
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="审批管理员" value="approval_admin" />
            <el-option label="运维人员" value="operator" />
            <el-option label="只读用户" value="readonly" />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">
          确定
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, RefreshRight } from '@element-plus/icons-vue'

const loading = ref(false)
const menuList = ref([])
const hasMenus = ref(false)
const formRef = ref(null)

// 可用图标列表
const iconOptions = [
  'DataAnalysis', 'Server', 'Collection', 'Document', 'Stamp', 'Monitor',
  'TrendCharts', 'Timer', 'Setting', 'User', 'UserFilled', 'ChatDotRound',
  'Tickets', 'Menu', 'HomeFilled', 'House', 'Grid', 'List', 'Operation',
  'Tools', 'Warning', 'InfoFilled', 'SuccessFilled', 'CircleCheck',
  'Bell', 'Message', 'Promotion', 'Upload', 'Download', 'Search'
]

const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false,
  currentId: null,
  form: {
    parent_id_path: null,
    name: '',
    path: '',
    icon: '',
    sort_order: 0,
    is_visible: true,
    is_enabled: true,
    roleList: []
  },
  rules: {
    name: [{ required: true, message: '请输入菜单名称', trigger: 'blur' }]
  }
})

// 父级菜单选项
const parentOptions = computed(() => {
  const buildOptions = (menus) => {
    return menus.map(menu => ({
      id: menu.id,
      name: menu.name,
      children: menu.children ? buildOptions(menu.children) : undefined
    }))
  }
  return buildOptions(menuList.value)
})

// 角色标签
const getRoleLabel = (role) => {
  const labels = {
    super_admin: '超管',
    approval_admin: '审批管理',
    operator: '运维',
    readonly: '只读'
  }
  return labels[role] || role
}

// 获取菜单列表
const fetchMenus = async () => {
  loading.value = true
  try {
    menuList.value = await request.get('/menu/list')
    hasMenus.value = menuList.value.length > 0
  } catch (error) {
    console.error('获取菜单列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 初始化默认菜单
const initDefaultMenus = async () => {
  try {
    await ElMessageBox.confirm(
      '将初始化系统默认菜单配置，是否继续？',
      '初始化菜单',
      { type: 'warning' }
    )
    
    await request.post('/menu/init-default')
    ElMessage.success('初始化成功')
    fetchMenus()
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || '初始化失败'
      ElMessage.error(errorMsg)
    }
  }
}

// 添加菜单
const handleAdd = (parent) => {
  dialog.isEdit = false
  dialog.currentId = null
  dialog.form = {
    parent_id_path: parent ? parent.id : null,
    name: '',
    path: '',
    icon: '',
    sort_order: 0,
    is_visible: true,
    is_enabled: true,
    roleList: []
  }
  dialog.visible = true
}

// 编辑菜单
const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.currentId = row.id
  dialog.form = {
    parent_id_path: row.parent_id,
    name: row.name,
    path: row.path || '',
    icon: row.icon || '',
    sort_order: row.sort_order,
    is_visible: row.is_visible,
    is_enabled: row.is_enabled,
    roleList: row.roles ? row.roles.split(',').map(r => r.trim()) : []
  }
  dialog.visible = true
}

// 删除菜单
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除菜单「${row.name}」吗？`,
      '删除确认',
      { type: 'warning' }
    )
    
    await request.delete(`/menu/${row.id}`)
    ElMessage.success('删除成功')
    fetchMenus()
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || '删除失败'
      ElMessage.error(errorMsg)
    }
  }
}

// 提交
const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.submitting = true
    try {
      const data = {
        parent_id: dialog.form.parent_id_path || null,
        name: dialog.form.name,
        path: dialog.form.path || null,
        icon: dialog.form.icon || null,
        sort_order: dialog.form.sort_order,
        is_visible: dialog.form.is_visible,
        is_enabled: dialog.form.is_enabled,
        roles: dialog.form.roleList.length > 0 ? dialog.form.roleList.join(',') : null
      }
      
      if (dialog.isEdit) {
        await request.put(`/menu/${dialog.currentId}`, data)
        ElMessage.success('更新成功')
      } else {
        await request.post('/menu', data)
        ElMessage.success('添加成功')
      }
      
      dialog.visible = false
      fetchMenus()
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '操作失败'
      ElMessage.error(errorMsg)
    } finally {
      dialog.submitting = false
    }
  })
}

onMounted(() => {
  fetchMenus()
})
</script>

<style lang="scss" scoped>
.menu-config-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }
  
  .table-operations {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-button + .el-button {
      margin-left: 0;
    }
  }
}
</style>
