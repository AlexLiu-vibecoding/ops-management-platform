<template>
  <div class="user-center-page">
    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="config-tabs">
      <el-tab-pane label="用户管理" name="users">
        <template #label>
          <span class="tab-label">
            <el-icon><User /></el-icon>
            用户管理
            <el-badge v-if="userCount > 0" :value="userCount" :max="99" class="tab-badge" />
          </span>
        </template>
      </el-tab-pane>
      <el-tab-pane label="注册审批" name="registrations">
        <template #label>
          <span class="tab-label">
            <el-icon><UserFilled /></el-icon>
            注册审批
            <el-badge v-if="pendingCount > 0" :value="pendingCount" :max="99" class="tab-badge" type="warning" />
          </span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- 用户管理内容 -->
    <div v-show="activeTab === 'users'" class="tab-content">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <el-form :inline="true" :model="searchForm" class="search-form">
              <el-form-item label="角色">
                <el-select v-model="searchForm.role" placeholder="全部角色" clearable style="width: 140px;">
                  <el-option v-for="role in roles" :key="role.value" :label="role.label" :value="role.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="状态">
                <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 100px;">
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
            <el-button type="primary" @click="handleAddUser">
              <el-icon><Plus /></el-icon>
              添加用户
            </el-button>
          </div>
        </template>
        
        <el-table :data="userList" style="width: 100%" v-loading="usersLoading" :show-overflow-tooltip="false">
          <el-table-column prop="username" label="用户名" min-width="80" />
          <el-table-column prop="real_name" label="姓名" min-width="70" />
          <el-table-column prop="email" label="邮箱" min-width="120" />
          <el-table-column prop="phone" label="电话" width="110" />
          <el-table-column prop="role" label="角色" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getRoleTagType(row.role)" size="small">
                {{ getRoleName(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" min-width="80" align="center">
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
          <el-table-column label="操作" min-width="100" fixed="right" align="center">
            <template #default="{ row }">
              <TableActions :row="row" :actions="userActions" @edit="handleEditUser" @resetPwd="handleResetPwd" @delete="handleDeleteUser" />
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
          style="margin-top: 16px; justify-content: flex-end;"
        />
      </el-card>
    </div>

    <!-- 注册审批内容 -->
    <div v-show="activeTab === 'registrations'" class="tab-content">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <el-select v-model="statusFilter" placeholder="筛选状态" style="width: 120px;" @change="fetchRegistrations">
                <el-option label="全部" value="" />
                <el-option label="待审批" value="pending" />
                <el-option label="已通过" value="approved" />
                <el-option label="已拒绝" value="rejected" />
              </el-select>
            </div>
            <el-button @click="fetchRegistrations">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </template>
        
        <el-table :data="registrations" style="width: 100%" v-loading="regsLoading" :show-overflow-tooltip="false">
          <el-table-column prop="username" label="用户名" min-width="100" />
          <el-table-column prop="real_name" label="姓名" min-width="80" />
          <el-table-column prop="email" label="邮箱" min-width="150" />
          <el-table-column prop="phone" label="手机号" min-width="120">
            <template #default="{ row }">{{ row.phone || '-' }}</template>
          </el-table-column>
          <el-table-column prop="reason" label="申请理由" min-width="150">
            <template #default="{ row }">{{ row.reason || '-' }}</template>
          </el-table-column>
          <el-table-column label="状态" min-width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="申请时间" min-width="160">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="reviewer_name" label="审批人" min-width="100">
            <template #default="{ row }">{{ row.reviewer_name || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" min-width="140" fixed="right" align="center">
            <template #default="{ row }">
              <template v-if="row.status === 'pending'">
                <el-button type="success" size="small" @click="handleReview(row, true)">通过</el-button>
                <el-button type="danger" size="small" @click="handleReview(row, false)">拒绝</el-button>
              </template>
              <el-button v-else type="primary" text size="small" @click="showDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 添加/编辑用户对话框 -->
    <el-dialog v-model="userDialog.visible" :title="userDialog.isEdit ? '编辑用户' : '添加用户'" width="500px" @close="resetUserForm">
      <el-form ref="userFormRef" :model="userDialog.form" :rules="userDialog.rules" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="userDialog.form.username" placeholder="请输入用户名" :disabled="userDialog.isEdit" />
        </el-form-item>
        <el-form-item label="姓名" prop="real_name">
          <el-input v-model="userDialog.form.real_name" placeholder="请输入姓名" />
        </el-form-item>
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userDialog.form.email" placeholder="请输入邮箱" />
        </el-form-item>
        <el-form-item label="电话" prop="phone">
          <el-input v-model="userDialog.form.phone" placeholder="请输入电话" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userDialog.form.role" placeholder="请选择角色" style="width: 100%;">
            <el-option v-for="role in roles" :key="role.value" :label="role.label" :value="role.value">
              <span>{{ role.label }}</span>
              <span style="color: #999; font-size: 12px; margin-left: 8px;">{{ role.description }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item v-if="!userDialog.isEdit" label="密码" prop="password">
          <el-input v-model="userDialog.form.password" type="password" show-password placeholder="请输入密码" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-switch v-model="userDialog.form.status" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="userDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitUser" :loading="userDialog.loading">
          {{ userDialog.isEdit ? '保存' : '添加' }}
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
          <el-input v-model="resetPwdDialog.form.newPassword" type="password" show-password placeholder="请输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitResetPwd" :loading="resetPwdDialog.loading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 注册详情对话框 -->
    <el-dialog v-model="detailVisible" title="注册申请详情" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ detailData?.username }}</el-descriptions-item>
        <el-descriptions-item label="真实姓名">{{ detailData?.real_name }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detailData?.email }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ detailData?.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请理由">{{ detailData?.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailData?.status)" size="small">
            {{ getStatusLabel(detailData?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ formatTime(detailData?.created_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="detailData?.reviewer_name" label="审批人">{{ detailData?.reviewer_name }}</el-descriptions-item>
        <el-descriptions-item v-if="detailData?.review_time" label="审批时间">{{ formatTime(detailData?.review_time) }}</el-descriptions-item>
        <el-descriptions-item v-if="detailData?.review_comment" label="审批意见">{{ detailData?.review_comment }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import { usersApi } from '@/api/users'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, UserFilled, Plus, Search, Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

// Tab 状态
const activeTab = ref('users')
const userCount = ref(0)
const pendingCount = ref(0)

// 用户操作列配置
const userActions = computed(() => [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { 
    key: 'resetPwd', 
    label: '重置密码', 
    event: 'resetPwd', 
    primary: false,
    visible: (row) => row.id !== currentUserId.value 
  },
  { 
    key: 'delete', 
    label: '删除', 
    event: 'delete', 
    danger: true, 
    primary: false,
    visible: (row) => row.id !== currentUserId.value 
  }
])

// ==================== 用户管理 ====================
const usersLoading = ref(false)
const userList = ref([])
const roles = ref([])
const userFormRef = ref(null)

const searchForm = reactive({
  role: null,
  status: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const userDialog = reactive({
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
  form: { newPassword: '' }
})

const fetchRoles = async () => {
  try {
    const data = await request.get('/permissions/roles/list')
    roles.value = data.items || []
  } catch (error) {
    console.error('获取角色列表失败:', error)
  }
}

const fetchUsers = async () => {
  usersLoading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      ...searchForm
    }
    const data = await usersApi.getList(params)
    userList.value = data.items || data
    pagination.total = data.total || data.length || 0
    userCount.value = pagination.total
  } catch (error) {
    console.error('获取用户列表失败:', error)
  } finally {
    usersLoading.value = false
  }
}

const handleSearch = () => {
  pagination.page = 1
  fetchUsers()
}

const handleReset = () => {
  searchForm.role = null
  searchForm.status = null
  handleSearch()
}

const handleAddUser = () => {
  userDialog.isEdit = false
  userDialog.form = {
    username: '',
    real_name: '',
    email: '',
    phone: '',
    role: 'readonly',
    password: '',
    status: true
  }
  userDialog.visible = true
}

const handleEditUser = (row) => {
  userDialog.isEdit = true
  userDialog.form = {
    id: row.id,
    username: row.username,
    real_name: row.real_name,
    email: row.email,
    phone: row.phone,
    role: row.role,
    status: row.status
  }
  userDialog.visible = true
}

const handleDeleteUser = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该用户吗？', '警告', { type: 'warning' })
    await usersApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleResetPwd = (row) => {
  resetPwdDialog.userId = row.id
  resetPwdDialog.username = row.username
  resetPwdDialog.form.newPassword = ''
  resetPwdDialog.visible = true
}

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

const handleSubmitUser = async () => {
  if (!userFormRef.value) return
  
  await userFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    userDialog.loading = true
    try {
      if (userDialog.isEdit) {
        await usersApi.update(userDialog.form.id, userDialog.form)
        ElMessage.success('更新成功')
      } else {
        await usersApi.create(userDialog.form)
        ElMessage.success('添加成功')
      }
      userDialog.visible = false
      fetchUsers()
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      userDialog.loading = false
    }
  })
}

const resetUserForm = () => {
  userDialog.form = {
    username: '',
    real_name: '',
    email: '',
    phone: '',
    role: 'readonly',
    password: '',
    status: true
  }
}

// ==================== 注册审批 ====================
const regsLoading = ref(false)
const registrations = ref([])
const statusFilter = ref('pending')
const detailVisible = ref(false)
const detailData = ref(null)

const fetchRegistrations = async () => {
  regsLoading.value = true
  try {
    const params = {}
    if (statusFilter.value) {
      params.status_filter = statusFilter.value
    }
    const data = await request.get('/auth/registrations', { params })
    registrations.value = data || []
    
    // 计算待审批数量
    if (statusFilter.value !== 'pending') {
      const allData = await request.get('/auth/registrations', { params: { status_filter: 'pending' } })
      pendingCount.value = (allData || []).length
    } else {
      pendingCount.value = registrations.value.length
    }
  } catch (error) {
    console.error('获取注册列表失败:', error)
    ElMessage.error('获取注册列表失败')
  } finally {
    regsLoading.value = false
  }
}

const handleReview = async (row, approved) => {
  try {
    const action = approved ? '通过' : '拒绝'
    const { value } = await ElMessageBox.prompt(
      `确定要${action}该注册申请吗？`,
      `${action}申请`,
      {
        inputType: 'textarea',
        inputPlaceholder: '请输入审批意见（可选）',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    await request.post(`/auth/registrations/${row.id}/review`, {
      approved: approved,
      comment: value || ''
    })
    
    ElMessage.success(`已${action}该注册申请`)
    fetchRegistrations()
    fetchUsers() // 刷新用户列表
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || '操作失败'
      ElMessage.error(errorMsg)
    }
  }
}

const showDetail = (row) => {
  detailData.value = row
  detailVisible.value = true
}

// ==================== 工具函数 ====================
const formatTime = (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

const getRoleName = (role) => {
  const roleItem = roles.value.find(r => r.value === role)
  return roleItem?.label || role
}

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

const getStatusType = (status) => {
  const types = { pending: 'warning', approved: 'success', rejected: 'danger' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { pending: '待审批', approved: '已通过', rejected: '已拒绝' }
  return labels[status] || status
}

onMounted(() => {
  fetchRoles()
  fetchUsers()
  fetchRegistrations()
})
</script>

<style lang="scss" scoped>
.user-center-page {
  .config-tabs {
    margin-bottom: 16px;
    
    :deep(.el-tabs__header) {
      margin: 0;
    }
    
    :deep(.el-tabs__nav-wrap::after) {
      display: none;
    }
    
    :deep(.el-tabs__item) {
      padding: 0 20px;
      height: 40px;
      line-height: 40px;
      
      &.is-active {
        font-weight: 600;
      }
    }
  }
  
  .tab-label {
    display: flex;
    align-items: center;
    gap: 6px;
    
    .el-icon {
      font-size: 16px;
    }
    
    .tab-badge {
      margin-left: 4px;
      
      :deep(.el-badge__content) {
        font-size: 10px;
        height: 14px;
        line-height: 14px;
        padding: 0 4px;
      }
    }
  }
  
  .tab-content {
    animation: fadeIn 0.2s ease;
  }
  
  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    
    .search-form {
      margin: 0;
      
      :deep(.el-form-item) {
        margin-bottom: 0;
      }
    }
  }
}

// 强制覆盖 Element Plus 表格截断样式
:deep(.el-table) {
  .el-table__cell {
    text-overflow: unset !important;
    overflow: visible !important;
  }
  
  .cell {
    text-overflow: unset !important;
    overflow: visible !important;
    white-space: normal !important;
    
    &.el-tooltip {
      white-space: nowrap !important;
      overflow: visible !important;
      text-overflow: unset !important;
    }
  }
  
  .el-tag {
    white-space: nowrap !important;
  }
}
</style>
