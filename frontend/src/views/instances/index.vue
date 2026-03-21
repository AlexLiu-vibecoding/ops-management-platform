<template>
  <div class="instances-page">
    <!-- 搜索和操作栏 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="环境">
          <el-select v-model="searchForm.environment_id" placeholder="全部环境" clearable style="width: 150px;">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="searchForm.status" placeholder="全部状态" clearable style="width: 120px;">
            <el-option label="在线" :value="true" />
            <el-option label="离线" :value="false" />
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
        添加实例
      </el-button>
    </el-card>
    
    <!-- 实例列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="instanceList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="实例名称" width="180" />
        <el-table-column label="地址" width="200">
          <template #default="{ row }">
            {{ row.host }}:{{ row.port }}
          </template>
        </el-table-column>
        <el-table-column label="环境" width="120">
          <template #default="{ row }">
            <span
              v-if="row.environment"
              class="env-tag"
              :style="{ backgroundColor: row.environment.color }"
            >
              {{ row.environment.name }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleView(row)">详情</el-button>
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="primary" @click="handleTest(row)">测试连接</el-button>
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchInstances"
        @current-change="fetchInstances"
      />
    </el-card>
    
    <!-- 添加/编辑实例对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑实例' : '添加实例'"
      width="600px"
      @close="resetForm"
    >
      <el-form
        ref="instanceFormRef"
        :model="dialog.form"
        :rules="dialog.rules"
        label-width="100px"
      >
        <el-form-item label="实例名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入实例名称" />
        </el-form-item>
        <el-row>
          <el-col :span="16">
            <el-form-item label="主机地址" prop="host">
              <el-input v-model="dialog.form.host" placeholder="请输入主机地址" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="端口" prop="port">
              <el-input v-model="dialog.form.port" placeholder="3306" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialog.form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="dialog.form.password"
            type="password"
            show-password
            placeholder="请输入密码"
          />
        </el-form-item>
        <el-form-item label="环境" prop="environment_id">
          <el-select v-model="dialog.form.environment_id" placeholder="请选择环境" style="width: 100%;">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="dialog.form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.loading">
          {{ dialog.isEdit ? '保存' : '测试并添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

const router = useRouter()

const loading = ref(false)
const instanceList = ref([])
const environments = ref([])

const searchForm = reactive({
  environment_id: null,
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
    name: '',
    host: '',
    port: 3306,
    username: '',
    password: '',
    environment_id: null,
    description: ''
  },
  rules: {
    name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
    host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
    port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
    username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
  }
})

const instanceFormRef = ref(null)

// 获取环境列表
const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data.items || data
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

// 获取实例列表
const fetchInstances = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      ...searchForm
    }
    const data = await instancesApi.getList(params)
    instanceList.value = data
    pagination.total = data.length
  } catch (error) {
    console.error('获取实例列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchInstances()
}

// 重置
const handleReset = () => {
  searchForm.environment_id = null
  searchForm.status = null
  handleSearch()
}

// 添加实例
const handleAdd = () => {
  dialog.isEdit = false
  dialog.visible = true
}

// 编辑实例
const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.visible = true
  dialog.form = { ...row, password: '' }
}

// 查看详情
const handleView = (row) => {
  router.push(`/instances/${row.id}`)
}

// 测试连接
const handleTest = async (row) => {
  try {
    ElMessage.info('正在测试连接...')
    const result = await instancesApi.checkStatus(row.id)
    if (result.success) {
      ElMessage.success(`连接成功，数据库版本: ${result.version}`)
    } else {
      ElMessage.error(result.message)
    }
    fetchInstances()
  } catch (error) {
    console.error('测试连接失败:', error)
  }
}

// 删除实例
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该实例吗？', '警告', {
      type: 'warning'
    })
    await instancesApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchInstances()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 提交表单
const handleSubmit = async () => {
  if (!instanceFormRef.value) return
  
  await instanceFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.loading = true
    try {
      // 处理端口数据，确保是数字
      const formData = {
        ...dialog.form,
        port: parseInt(dialog.form.port) || 3306
      }
      
      if (dialog.isEdit) {
        await instancesApi.update(formData.id, formData)
        ElMessage.success('更新成功')
      } else {
        // 先测试连接
        const testResult = await instancesApi.testConnection(formData)
        if (!testResult.success) {
          ElMessage.error(`连接测试失败: ${testResult.message}`)
          return
        }
        
        await instancesApi.create(formData)
        ElMessage.success('添加成功')
      }
      
      dialog.visible = false
      fetchInstances()
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      dialog.loading = false
    }
  })
}

// 重置表单
const resetForm = () => {
  dialog.form = {
    name: '',
    host: '',
    port: 3306,
    username: '',
    password: '',
    environment_id: null,
    description: ''
  }
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchEnvironments()
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.instances-page {
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
}
</style>
