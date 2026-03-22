<template>
  <div class="users-page">
    <!-- 搜索和操作栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="角色">
          <el-select v-model="searchForm.role" placeholder="全部角色" clearable style="width: 150px;">
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="审批管理员" value="approval_admin" />
            <el-option label="运维人员" value="operator" />
            <el-option label="只读用户" value="readonly" />
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
        <el-table-column prop="username" label="用户名" width="120" />
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column prop="email" label="邮箱" width="200" />
        <el-table-column prop="phone" label="电话" width="130" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" size="small">
              {{ getRoleName(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login_time" label="最后登录" width="180">
          <template #default="{ row }">
            {{ row.last_login_time ? formatTime(row.last_login_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="primary" size="small" @click="handleResetPwd(row)" :disabled="row.id === currentUserId">重置密码</el-button>
              <el-button link type="primary" size="small" @click="handleBindEnv(row)">环境权限</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)" :disabled="row.id === currentUserId">删除</el-button>
            </div>
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
            <el-option label="超级管理员" value="super_admin" />
            <el-option label="审批管理员" value="approval_admin" />
            <el-option label="运维人员" value="operator" />
            <el-option label="只读用户" value="readonly" />
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
    
    <!-- 环境权限绑定对话框 -->
    <el-dialog v-model="envDialog.visible" title="环境权限绑定" width="500px">
      <el-form label-width="80px">
        <el-form-item label="用户">
          <el-input :value="envDialog.username" disabled />
        </el-form-item>
        <el-form-item label="环境">
          <el-checkbox-group v-model="envDialog.selectedEnvs">
            <el-checkbox
              v-for="env in environments"
              :key="env.id"
              :label="env.id"
              :value="env.id"
            >
              <span :style="{ color: env.color }">{{ env.name }}</span>
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="envDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBindEnv" :loading="envDialog.loading">保存</el-button>
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
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const loading = ref(false)
const userList = ref([])
const environments = ref([])

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
  visible: false,
  loading: false,
  userId: null,
  username: '',
  selectedEnvs: []
})

const userFormRef = ref(null)

// 获取环境列表
const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data.items || data
  } catch (error) {
    console.error('获取环境列表失败:', error)
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
    userList.value = data
    pagination.total = data.length
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

// 环境权限
const handleBindEnv = async (row) => {
  envDialog.userId = row.id
  envDialog.username = row.username
  
  // 获取用户已绑定的环境
  // TODO: 后端需要添加接口获取用户环境绑定
  
  envDialog.selectedEnvs = []
  envDialog.visible = true
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

// 提交环境绑定
const submitBindEnv = async () => {
  envDialog.loading = true
  try {
    await usersApi.bindEnvironments(envDialog.userId, envDialog.selectedEnvs)
    ElMessage.success('环境权限绑定成功')
    envDialog.visible = false
  } catch (error) {
    console.error('绑定失败:', error)
  } finally {
    envDialog.loading = false
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

// 获取角色名称
const getRoleName = (role) => {
  const roleMap = {
    super_admin: '超级管理员',
    approval_admin: '审批管理员',
    operator: '运维人员',
    readonly: '只读用户'
  }
  return roleMap[role] || role
}

// 获取角色标签类型
const getRoleTagType = (role) => {
  const typeMap = {
    super_admin: 'danger',
    approval_admin: 'warning',
    operator: 'primary',
    readonly: 'info'
  }
  return typeMap[role] || 'info'
}

onMounted(() => {
  fetchEnvironments()
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
