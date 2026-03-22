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
      
      <el-button type="primary" @click="handleAdd" v-if="canOperate">
        <el-icon><Plus /></el-icon>
        添加实例
      </el-button>
    </el-card>
    
    <!-- 实例列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="instanceList" style="width: 100%" v-loading="loading">
        <el-table-column prop="name" label="实例名称" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <div>
              <span>{{ row.name }}</span>
              <el-tag v-if="row.is_rds" type="warning" size="small" style="margin-left: 4px;">RDS</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag 
              :type="row.db_type === 'postgresql' ? 'success' : row.db_type === 'redis' ? 'warning' : 'primary'" 
              size="small"
            >
              {{ row.db_type === 'postgresql' ? 'PostgreSQL' : row.db_type === 'redis' ? 'Redis' : 'MySQL' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="地址" min-width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.is_rds && row.rds_instance_id">
              {{ row.rds_instance_id }}
              <span v-if="row.aws_region" style="color: #999;">({{ row.aws_region }})</span>
            </span>
            <span v-else>{{ row.host }}:{{ row.port }}</span>
          </template>
        </el-table-column>
        <el-table-column label="环境" min-width="90" align="center">
          <template #default="{ row }">
            <span
              v-if="row.environment"
              class="env-tag"
              :style="{ backgroundColor: row.environment.color, color: '#FFFFFF' }"
            >
              {{ row.environment.name }}
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'danger'" size="small">
              {{ row.status ? '在线' : '离线' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="100" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleView(row)">详情</el-button>
              <el-button link type="primary" size="small" @click="handleEdit(row)" v-if="canOperate">编辑</el-button>
              <el-button link type="primary" size="small" @click="handleTest(row)">测试</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)" v-if="canOperate">删除</el-button>
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
        @size-change="fetchInstances"
        @current-change="fetchInstances"
      />
    </el-card>
    
    <!-- 添加/编辑实例对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑实例' : '添加实例'"
      width="650px"
      @close="resetForm"
    >
      <el-form
        ref="instanceFormRef"
        :model="dialog.form"
        :rules="getFullRules()"
        label-width="110px"
      >
        <el-form-item label="实例名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入实例名称" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="数据库类型" prop="db_type">
              <el-select v-model="dialog.form.db_type" placeholder="请选择数据库类型" style="width: 100%;">
                <el-option label="MySQL" value="mysql" />
                <el-option label="PostgreSQL" value="postgresql" />
                <el-option label="Redis" value="redis" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
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
          </el-col>
        </el-row>
        
        <!-- 状态开关 -->
        <el-form-item label="状态">
          <el-switch
            v-model="dialog.form.status"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
        
        <!-- AWS RDS 配置 (仅 MySQL/PostgreSQL) -->
        <template v-if="dialog.form.db_type !== 'redis'">
          <el-divider content-position="left">
            <el-checkbox v-model="dialog.form.is_rds" :label="'AWS RDS 实例'" />
          </el-divider>
          
          <el-row :gutter="20" v-if="dialog.form.is_rds">
            <el-col :span="12">
              <el-form-item label="RDS 实例ID" prop="rds_instance_id">
                <el-input v-model="dialog.form.rds_instance_id" placeholder="如: my-db-instance" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="AWS 区域" prop="aws_region">
                <el-select 
                  v-model="dialog.form.aws_region" 
                  placeholder="请选择或输入区域" 
                  style="width: 100%;"
                  filterable
                  allow-create
                  default-first-option
                >
                  <el-option-group label="美洲">
                    <el-option label="us-east-1 (弗吉尼亚北部)" value="us-east-1" />
                    <el-option label="us-east-2 (俄亥俄)" value="us-east-2" />
                    <el-option label="us-west-1 (加利福尼亚北部)" value="us-west-1" />
                    <el-option label="us-west-2 (俄勒冈)" value="us-west-2" />
                    <el-option label="af-south-1 (开普敦)" value="af-south-1" />
                    <el-option label="sa-east-1 (圣保罗)" value="sa-east-1" />
                    <el-option label="ca-central-1 (加拿大中部)" value="ca-central-1" />
                    <el-option label="me-south-1 (巴林)" value="me-south-1" />
                  </el-option-group>
                  <el-option-group label="欧洲">
                    <el-option label="eu-west-1 (爱尔兰)" value="eu-west-1" />
                    <el-option label="eu-west-2 (伦敦)" value="eu-west-2" />
                    <el-option label="eu-west-3 (巴黎)" value="eu-west-3" />
                    <el-option label="eu-south-1 (米兰)" value="eu-south-1" />
                    <el-option label="eu-central-1 (法兰克福)" value="eu-central-1" />
                    <el-option label="eu-north-1 (斯德哥尔摩)" value="eu-north-1" />
                  </el-option-group>
                  <el-option-group label="亚太">
                    <el-option label="ap-northeast-1 (东京)" value="ap-northeast-1" />
                    <el-option label="ap-northeast-2 (首尔)" value="ap-northeast-2" />
                    <el-option label="ap-northeast-3 (大阪)" value="ap-northeast-3" />
                    <el-option label="ap-southeast-1 (新加坡)" value="ap-southeast-1" />
                    <el-option label="ap-southeast-2 (悉尼)" value="ap-southeast-2" />
                    <el-option label="ap-southeast-3 (雅加达)" value="ap-southeast-3" />
                    <el-option label="ap-south-1 (孟买)" value="ap-south-1" />
                    <el-option label="ap-east-1 (香港)" value="ap-east-1" />
                  </el-option-group>
                  <el-option-group label="中国">
                    <el-option label="cn-north-1 (北京)" value="cn-north-1" />
                    <el-option label="cn-northwest-1 (宁夏)" value="cn-northwest-1" />
                  </el-option-group>
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </template>
        
        <!-- 直连配置 - 始终显示 -->
        <el-divider content-position="left">{{ dialog.form.db_type === 'redis' ? 'Redis 连接配置' : (dialog.form.is_rds ? '直连配置（可选，用于直接连接 RDS）' : '直连配置') }}</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="16">
            <el-form-item label="主机地址" :prop="dialog.form.is_rds ? '' : 'host'">
              <el-input v-model="dialog.form.host" :placeholder="dialog.form.is_rds ? 'RDS 端点地址（可选）' : '请输入主机地址'" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="端口" :prop="dialog.form.is_rds ? '' : 'port'">
              <el-input v-model="dialog.form.port" :placeholder="dialog.form.db_type === 'postgresql' ? '5432' : dialog.form.db_type === 'redis' ? '6379' : '3306'" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <!-- MySQL/PostgreSQL 需要用户名 -->
        <el-form-item label="用户名" :prop="dialog.form.is_rds ? '' : 'username'" v-if="dialog.form.db_type !== 'redis'">
          <el-input v-model="dialog.form.username" :placeholder="dialog.form.is_rds ? 'RDS 用户名（可选）' : '请输入用户名'" />
        </el-form-item>
        <!-- 密码 -->
        <el-form-item :label="dialog.form.db_type === 'redis' ? '密码' : '密码'" :prop="dialog.form.is_rds ? '' : 'password'">
          <el-input
            v-model="dialog.form.password"
            type="password"
            show-password
            :placeholder="dialog.isEdit ? '留空则不修改密码' : (dialog.form.is_rds ? 'RDS 密码（可选）' : (dialog.form.db_type === 'redis' ? '请输入 Redis 密码（如有）' : '请输入密码'))"
          />
        </el-form-item>
        
        <!-- Redis 特有配置 -->
        <template v-if="dialog.form.db_type === 'redis'">
          <el-form-item label="运行模式">
            <el-select v-model="dialog.form.redis_mode" placeholder="请选择运行模式" style="width: 100%;">
              <el-option label="单机模式" value="standalone" />
              <el-option label="集群模式" value="cluster" />
              <el-option label="哨兵模式" value="sentinel" />
            </el-select>
          </el-form-item>
        </template>
        
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
import { ref, reactive, onMounted, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

// 操作权限：管理员和运维人员可以操作
const canOperate = computed(() => {
  const role = userStore.user?.role
  return ['super_admin', 'approval_admin', 'operator'].includes(role)
})

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
    db_type: 'mysql',
    host: '',
    port: 3306,
    username: '',
    password: '',
    environment_id: null,
    description: '',
    status: true,
    is_rds: false,
    rds_instance_id: '',
    aws_region: '',
    redis_mode: 'standalone',
    redis_db: 0
  },
  rules: {
    name: [{ required: true, message: '请输入实例名称', trigger: 'blur' }],
    db_type: [{ required: true, message: '请选择数据库类型', trigger: 'change' }],
    rds_instance_id: [{ required: true, message: '请输入 RDS 实例ID', trigger: 'blur' }],
    aws_region: [{ required: true, message: '请选择 AWS 区域', trigger: 'change' }]
  }
})

// 动态验证规则 - 直连实例需要 host/port，MySQL/PostgreSQL 需要 username
// RDS 实例时，直连配置可选
const getConnectionRules = () => {
  // RDS 模式下直连配置可选
  if (dialog.form.is_rds) {
    return {}
  }
  const rules = {
    host: [{ required: true, message: '请输入主机地址', trigger: 'blur' }],
    port: [{ required: true, message: '请输入端口', trigger: 'blur' }]
  }
  // MySQL/PostgreSQL 需要用户名
  if (dialog.form.db_type !== 'redis') {
    rules.username = [{ required: true, message: '请输入用户名', trigger: 'blur' }]
  }
  return rules
}

// 密码验证规则 - 新增时 MySQL/PostgreSQL 必填，Redis 可选
// RDS 模式下密码可选（可能通过 IAM 认证等）
const getPasswordRule = () => {
  if (dialog.isEdit) {
    return {}
  }
  if (dialog.form.is_rds) {
    return {}
  }
  // Redis 密码可选
  if (dialog.form.db_type === 'redis') {
    return {}
  }
  return {
    password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
  }
}

// 获取完整验证规则
const getFullRules = () => {
  return {
    ...dialog.rules,
    ...getConnectionRules(),
    ...getPasswordRule()
  }
}

const instanceFormRef = ref(null)

// 监听数据库类型变化，自动调整端口和 RDS 选项
watch(() => dialog.form.db_type, (newType, oldType) => {
  if (newType === 'redis') {
    dialog.form.is_rds = false
    // 如果端口是其他数据库的默认端口，改为 Redis 默认端口
    if (dialog.form.port === 3306 || dialog.form.port === 5432) {
      dialog.form.port = 6379
    }
  } else if (newType === 'postgresql') {
    if (dialog.form.port === 3306 || dialog.form.port === 6379) {
      dialog.form.port = 5432
    }
  } else if (newType === 'mysql') {
    if (dialog.form.port === 5432 || dialog.form.port === 6379) {
      dialog.form.port = 3306
    }
  }
})

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
    // API 返回格式: {total, items}
    instanceList.value = data.items || []
    pagination.total = data.total || 0
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
  dialog.form = {
    name: '',
    db_type: 'mysql',
    host: '',
    port: 3306,
    username: '',
    password: '',
    environment_id: null,
    description: '',
    status: true,
    is_rds: false,
    rds_instance_id: '',
    aws_region: '',
    redis_mode: 'standalone',
    redis_db: 0
  }
}

// 编辑实例
const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.visible = true
  dialog.form = {
    id: row.id,
    name: row.name,
    db_type: row.db_type || 'mysql',
    host: row.host || '',
    port: row.port || 3306,
    username: row.username || '',
    password: '', // 编辑时密码留空表示不修改
    environment_id: row.environment_id,
    description: row.description || '',
    status: row.status ?? true,
    is_rds: row.is_rds || false,
    rds_instance_id: row.rds_instance_id || '',
    aws_region: row.aws_region || '',
    redis_mode: row.redis_mode || 'standalone',
    redis_db: row.redis_db || 0
  }
}

// 查看详情
const handleView = (row) => {
  if (row.db_type === 'redis') {
    router.push(`/redis/${row.id}`)
  } else {
    router.push(`/instances/${row.id}`)
  }
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
      
      // 编辑模式下，如果密码为空则不传密码字段
      if (dialog.isEdit && !formData.password) {
        delete formData.password
      }
      
      // RDS 实例不需要连接信息
      if (formData.is_rds) {
        delete formData.host
        delete formData.port
        delete formData.username
        delete formData.password
      }
      
      if (dialog.isEdit) {
        await instancesApi.update(formData.id, formData)
        ElMessage.success('更新成功')
      } else {
        // 非RDS实例需要先测试连接
        if (!formData.is_rds) {
          const testResult = await instancesApi.testConnection(formData)
          if (!testResult.success) {
            ElMessage.error(`连接测试失败: ${testResult.message}`)
            return
          }
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
    db_type: 'mysql',
    host: '',
    port: 3306,
    username: '',
    password: '',
    environment_id: null,
    description: '',
    status: true,
    is_rds: false,
    rds_instance_id: '',
    aws_region: ''
  }
  dialog.isEdit = false
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
  
  .env-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    white-space: nowrap;
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
