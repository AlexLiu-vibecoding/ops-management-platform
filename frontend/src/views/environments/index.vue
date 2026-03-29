<template>
  <div class="environments-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>环境管理</span>
          <el-button type="primary" @click="handleAdd" v-if="isAdmin">
            <el-icon><Plus /></el-icon>
            添加环境
          </el-button>
        </div>
      </template>
      
      <el-alert
        title="AWS 配置说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #default>
          <p>各环境可配置独立的 AWS 凭证，用于采集该环境下 RDS 实例的 CloudWatch 性能指标。</p>
          <p style="margin-top: 4px;">适用于网络隔离场景，不同环境访问不同 AWS 账号。</p>
        </template>
      </el-alert>
      
      <el-table :data="environments" style="width: 100%">
        <el-table-column prop="name" label="环境名称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="code" label="环境编码" min-width="80" show-overflow-tooltip />
        <el-table-column label="颜色标记" width="100" align="center">
          <template #default="{ row }">
            <span class="env-tag" :style="{ backgroundColor: row.color, color: '#FFFFFF' }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="require_approval" label="需要审批" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.require_approval ? 'warning' : 'success'" size="small">
              {{ row.require_approval ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="AWS 配置" width="120" align="center">
          <template #default="{ row }">
            <el-tooltip v-if="row.aws_configured" :content="`区域: ${row.aws_region || '-'}`" placement="top">
              <el-tag type="success" size="small">
                <el-icon><Connection /></el-icon>
                已配置
              </el-tag>
            </el-tooltip>
            <el-tag v-else type="info" size="small">未配置</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'info'" size="small">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="100" show-overflow-tooltip />
        <el-table-column label="操作" width="160" v-if="isAdmin" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="envActions"
              :max-primary="2"
              @edit="handleEdit"
              @delete="handleDelete"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑环境' : '添加环境'" width="600px">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="120px" class="dialog-form">
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入环境名称" />
        </el-form-item>
        <el-form-item label="环境编码" prop="code">
          <el-input v-model="dialog.form.code" placeholder="请输入环境编码（如：development, production）" :disabled="dialog.isEdit" />
        </el-form-item>
        <el-form-item label="颜色标记" prop="color">
          <el-color-picker v-model="dialog.form.color" />
        </el-form-item>
        <el-form-item label="需要审批" prop="require_approval">
          <el-switch v-model="dialog.form.require_approval" />
          <span class="form-hint">开启后，该环境下的实例操作需要审批</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch
            v-model="dialog.form.status"
            active-text="启用"
            inactive-text="禁用"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="2" />
        </el-form-item>
        
        <el-divider content-position="left">
          <el-icon><Cloudy /></el-icon>
          AWS 配置（可选）
        </el-divider>
        
        <el-alert
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        >
          AWS 凭证用于采集 RDS 实例的 CloudWatch 性能指标，需具有 RDS 和 CloudWatch 只读权限。
        </el-alert>
        
        <el-form-item label="AWS 区域">
          <el-select v-model="dialog.form.aws_region" placeholder="选择 AWS 区域" style="width: 100%;">
            <el-option-group label="美国">
              <el-option label="美国东部 (弗吉尼亚北部)" value="us-east-1" />
              <el-option label="美国东部 (俄亥俄)" value="us-east-2" />
              <el-option label="美国西部 (加利福尼亚)" value="us-west-1" />
              <el-option label="美国西部 (俄勒冈)" value="us-west-2" />
            </el-option-group>
            <el-option-group label="亚太">
              <el-option label="亚太地区 (新加坡)" value="ap-southeast-1" />
              <el-option label="亚太地区 (悉尼)" value="ap-southeast-2" />
              <el-option label="亚太地区 (东京)" value="ap-northeast-1" />
              <el-option label="亚太地区 (首尔)" value="ap-northeast-2" />
              <el-option label="亚太地区 (香港)" value="ap-east-1" />
            </el-option-group>
            <el-option-group label="中国">
              <el-option label="中国 (北京)" value="cn-north-1" />
              <el-option label="中国 (宁夏)" value="cn-northwest-1" />
            </el-option-group>
            <el-option-group label="欧洲">
              <el-option label="欧洲 (法兰克福)" value="eu-central-1" />
              <el-option label="欧洲 (爱尔兰)" value="eu-west-1" />
              <el-option label="欧洲 (伦敦)" value="eu-west-2" />
            </el-option-group>
          </el-select>
        </el-form-item>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Access Key ID">
              <el-input 
                v-model="dialog.form.aws_access_key_id" 
                placeholder="AKIAIOSFODNN7EXAMPLE"
                show-password
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Secret Key">
              <el-input 
                v-model="dialog.form.aws_secret_access_key" 
                placeholder="wJalrXUtnFEMI..."
                show-password
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item>
          <el-button @click="testAwsConnection" :loading="testingAws" :disabled="!canTestAws">
            <el-icon><Connection /></el-icon>
            测试连接
          </el-button>
          <span class="form-hint" v-if="testResult">
            <el-icon v-if="testResult.success" style="color: #67C23A;"><SuccessFilled /></el-icon>
            <el-icon v-else style="color: #F56C6C;"><CircleCloseFilled /></el-icon>
            {{ testResult.message }}
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Cloudy, Connection, SuccessFilled, CircleCloseFilled, Edit, DeleteFilled } from '@element-plus/icons-vue'
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

// 环境操作配置
const envActions = computed(() => [
  { 
    key: 'edit', 
    label: '编辑', 
    event: 'edit', 
    primary: true,
    icon: Edit
  },
  { 
    key: 'delete', 
    label: '删除', 
    event: 'delete', 
    danger: true,
    icon: DeleteFilled
  }
])

const environments = ref([])
const formRef = ref(null)
const submitting = ref(false)
const testingAws = ref(false)
const testResult = ref(null)

const dialog = reactive({
  visible: false,
  isEdit: false,
  editingId: null,
  form: {
    name: '',
    code: '',
    color: '#52C41A',
    require_approval: true,
    status: true,
    description: '',
    aws_region: '',
    aws_access_key_id: '',
    aws_secret_access_key: ''
  },
  rules: {
    name: [{ required: true, message: '请输入环境名称', trigger: 'blur' }],
    code: [{ required: true, message: '请输入环境编码', trigger: 'blur' }]
  }
})

// 是否可以测试 AWS 连接
const canTestAws = computed(() => {
  return dialog.form.aws_access_key_id && 
         dialog.form.aws_secret_access_key && 
         dialog.form.aws_region
})

const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data.items || data
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

const resetForm = () => {
  dialog.form = {
    name: '',
    code: '',
    color: '#52C41A',
    require_approval: true,
    status: true,
    description: '',
    aws_region: '',
    aws_access_key_id: '',
    aws_secret_access_key: ''
  }
  testResult.value = null
}

const handleAdd = () => {
  dialog.isEdit = false
  dialog.editingId = null
  resetForm()
  dialog.visible = true
}

const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.editingId = row.id
  dialog.form = { 
    id: row.id,
    name: row.name, 
    code: row.code, 
    color: row.color, 
    require_approval: row.require_approval, 
    status: row.status ?? true,
    description: row.description || '',
    aws_region: row.aws_region || '',
    aws_access_key_id: '',  // 不回显密钥
    aws_secret_access_key: ''
  }
  testResult.value = null
  dialog.visible = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该环境吗？', '警告', { type: 'warning' })
    await request.delete(`/environments/${row.id}`)
    ElMessage.success('删除成功')
    fetchEnvironments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const testAwsConnection = async () => {
  testingAws.value = true
  testResult.value = null
  
  try {
    const result = await request.post(`/environments/${dialog.editingId || 0}/test-aws`, {
      aws_access_key_id: dialog.form.aws_access_key_id,
      aws_secret_access_key: dialog.form.aws_secret_access_key,
      aws_region: dialog.form.aws_region
    })
    testResult.value = result
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    testResult.value = {
      success: false,
      message: error.response?.data?.detail || '连接测试失败'
    }
  } finally {
    testingAws.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      // 构建提交数据，只包含有值的 AWS 配置
      const submitData = { ...dialog.form }
      if (!submitData.aws_access_key_id && !submitData.aws_secret_access_key) {
        delete submitData.aws_access_key_id
        delete submitData.aws_secret_access_key
        delete submitData.aws_region
      }
      
      if (dialog.isEdit) {
        await request.put(`/environments/${dialog.editingId}`, submitData)
        ElMessage.success('更新成功')
      } else {
        await request.post('/environments', submitData)
        ElMessage.success('添加成功')
      }
      dialog.visible = false
      fetchEnvironments()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  fetchEnvironments()
})
</script>

<style lang="scss" scoped>
.environments-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .table-operations {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-button + .el-button {
      margin-left: 0;
    }
  }
  
  .env-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
  }
  
  .form-hint {
    margin-left: 8px;
    color: #909399;
    font-size: 12px;
  }
  
  .dialog-form {
    .el-divider {
      margin: 20px 0 16px;
    }
  }
}
</style>
