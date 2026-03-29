<template>
  <div class="users-page">
    <!-- 搜索和操作栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="全部角色" clearable style="width: 150px;">
            <el-option
              v-for="role in roles"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 120px;">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
      
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon>
        添加用户
      </el-button>
    </el-card>
    
    <!-- 用户列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="userList" style="width: 100%" v-loading="loading">
        <el-table-column prop="username" label="用户名" min-width="80" show-overflow-tooltip />
        <el-table-column prop="real_name" label="姓名" min-width="70" show-overflow-tooltip />
        <el-table-column prop="email" label="邮箱" min-width="120" show-overflow-tooltip />
        <el-table-column prop="phone" label="电话" width="110" show-overflow-tooltip />
        <el-table-column prop="role" label="角色" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" size="small">
              {{ getRoleName(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_time" label="最后登录" width="160">
          <template #default="{ row }">
            {{ row.last_login_time ? formatTime(row.last_login_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="userActions"
              :max-primary="2"
              @edit="handleEdit"
              @resetPwd="handleResetPwd"
              @delete="handleDelete"
            />
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchUsers"
        @current-change="fetchUsers"
      />
    </el-card>
    
    <!-- 添加/编辑用户对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑用户' : '添加用户'"
      width="500px"
      @close="resetForm"
    >
      <el-form
        ref="userFormRef"
        :model="dialog.form"
        :rules="dialog.rules"
        label-width="80px"
        class="dialog-form"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialog.form.username" placeholder="请输入用户名" :disabled="dialog.isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="dialog.form.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="dialog.form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="dialog.form.phone" placeholder="请输入电话" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="dialog.form.role" placeholder="请选择角色" style="width: 100%;">
            <el-option
              v-for="role in roles"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            >
              <span>{{ role.label }}</span>
              <span style="color: #999; font-size: 12px; margin-left: 8px;">{{ role.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="密码" prop="password">
          <el-input
            v-model="dialog.form.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch v-model="dialog.form.status" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.loading">
          {{ dialog.isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetPwdDialog.visible" title="重置密码" width="400px">
      <el-form :model="resetPwdDialog.form" label-width="80px">
        <el-form-item label="用户">
          <el-input :value="resetPwdDialog.username" disabled />
        </el-form-item>
        <el-form-item label="新密码" required>
          <el-input
            v-model="resetPwdDialog.form.newPassword"
            type="password"
            show-password
            placeholder="请输入新密码"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitResetPwd" :loading="resetPwdDialog.loading">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 提示：环境权限由角色控制 -->
    <el-dialog v-model="envDialog.visible" title="环境权限说明" width="400px">
      <el-alert
        title="环境权限由角色控制"
        type="info"
        description="用户的环境权限由其所属角色决定，如需修改请前往角色管理页面配置角色的环境权限。"
        show-icon
        :closable="false"
      />
      <template #footer>
        <el-button type="primary" @click="envDialog.visible = false">我知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { usersApi } from '@/api/users'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Key, DeleteFilled } from '@element-plus/icons-vue'
import TableActions from '@/components/TableActions.vue'
import dayjs from 'dayjs'
import request from '@/api/index'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

// 用户操作配置
const userActions = computed(() => [
  { 
    key: 'edit', 
    label: '编辑', 
    event: 'edit', 
    primary: true,
    icon: Edit
  },
  { 
    key: 'resetPwd', 
    label: '重置密码', 
    event: 'resetPwd', 
    visible: (row) => row.id !== currentUserId.value,
    icon: Key
  },
  { 
    key: 'delete', 
    label: '删除', 
    event: 'delete', 
    visible: (row) => row.id !== currentUserId.value,
    danger: true,
    divided: true,
    icon: DeleteFilled
  }
])

const loading = ref(false)
const userList = ref([])
const roles = ref([])  // 动态角色列表

const searchForm = reactive({
  role: null,
  status: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  form: {
    username: '',
    real_name: '',
    email: '',
    phone: '',
    role: 'readonly',
    password: '',
    status: true
  },
  rules: {
    username: [
      { required: true, message: '请输入用户名', trigger: 'blur' },
      { min: 3, max: 50, message: '用户名长度3-50字符', trigger: 'blur' }
    ],
    real_name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
    email: [
      { required: true, message: '请输入邮箱', trigger: 'blur' },
      { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
    ],
    role: [{ required: true, message: '请选择角色', trigger: 'change' }],
    password: [
      { required: true, message: '请输入密码', trigger: 'blur' },
      { min: 6, max: 50, message: '密码长度6-50字符', trigger: 'blur' }
    ]
  }
})

const resetPwdDialog = reactive({
  visible: false,
  loading: false,
  userId: null,
  username: '',
  form: {
    newPassword: ''
  }
})

const envDialog = reactive({
  visible: false
})

const userFormRef = ref(null)

// 获取角色列表
const fetchRoles = async () => {
  try {
    const data = await request.get('/permissions/roles/list')
    roles.value = data.items || []
  } catch (error) {
    console.error('获取角色列表失败:', error)
  }
}

// 获取用户列表
const fetchUsers = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      ...searchForm
    }
    const data = await usersApi.getList(params)
    userList.value = data.items || data
    pagination.total = data.total || data.length || 0
  } catch (error) {
    console.error('获取用户列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchUsers()
}

// 重置
const handleReset = () => {
  searchForm.role = null
  searchForm.status = null
  handleSearch()
}

// 添加用户
const handleAdd = () => {
  dialog.isEdit = false
  dialog.visible = true
}

// 编辑用户
const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.visible = true
  dialog.form = {
    id: row.id,
    username: row.username,
    real_name: row.real_name,
    email: row.email,
    phone: row.phone,
    role: row.role,
    status: row.status
  }
}

// 重置密码
const handleResetPwd = (row) => {
  resetPwdDialog.userId = row.id
  resetPwdDialog.username = row.username
  resetPwdDialog.form.newPassword = ''
  resetPwdDialog.visible = true
}

// 删除用户
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？', '警告', {
      type: 'warning'
    })
    await usersApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!userFormRef.value) return
  
  await userFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.loading = true
    try {
      if (dialog.isEdit) {
        await usersApi.update(dialog.form.id, dialog.form)
        ElMessage.success('更新成功')
      } else {
        await usersApi.create(dialog.form)
        ElMessage.success('添加成功')
      }
      
      dialog.visible = false
      fetchUsers()
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      dialog.loading = false
    }
  })
}

// 提交重置密码
const submitResetPwd = async () => {
  if (!resetPwdDialog.form.newPassword) {
    ElMessage.warning('请输入新密码')
    return
  }
  
  if (resetPwdDialog.form.newPassword.length < 6) {
    ElMessage.warning('密码长度不能少于6位')
    return
  }
  
  resetPwdDialog.loading = true
  try {
    await usersApi.resetPassword(resetPwdDialog.userId, resetPwdDialog.form.newPassword)
    ElMessage.success('密码重置成功')
    resetPwdDialog.visible = false
  } catch (error) {
    console.error('重置密码失败:', error)
  } finally {
    resetPwdDialog.loading = false
  }
}

// 重置表单
const resetForm = () => {
  dialog.form = {
    username: '',
    real_name: '',
    email: '',
    phone: '',
    role: 'readonly',
    password: '',
    status: true
  }
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 获取角色名称（从动态列表获取）
const getRoleName = (role) => {
  const roleItem = roles.value.find(r => r.value === role)
  return roleItem?.label || role
}

// 获取角色标签类型
const getRoleTagType = (role) => {
  const typeMap = {
    super_admin: 'danger',
    approval_admin: 'warning',
    operator: 'primary',
    developer: 'success',
    readonly: 'info'
  }
  return typeMap[role] || 'info'
}

onMounted(() => {
  fetchRoles()
  fetchUsers()
})
</script>

<style lang="scss" scoped>
.users-page {
  .search-card {
    margin-bottom: 20px;
    
    :deep(.el-card__body) {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
  }
  
  .table-card {
    .el-pagination {
      margin-top: 20px;
      justify-content: flex-end;
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
