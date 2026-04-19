<template>
  <div class="environment-config-page">
    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="config-tabs" @tab-change="handleTabChange">
      <el-tab-pane label="环境管理" name="environments">
        <template #label>
          <span class="tab-label">
            <el-icon><Collection /></el-icon>
            环境管理
          </span>
        </template>
      </el-tab-pane>
      <el-tab-pane label="AWS区域" name="regions">
        <template #label>
          <span class="tab-label">
            <el-icon><Location /></el-icon>
            AWS区域
          </span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <!-- 环境管理内容 -->
    <div v-show="activeTab === 'environments'" class="tab-content">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span>环境列表</span>
              <el-tag type="info" size="small" style="margin-left: 8px;">{{ environments.length }} 个环境</el-tag>
            </div>
            <el-button type="primary" @click="handleAddEnv" v-if="canManageEnv">
              <el-icon><Plus /></el-icon>
              添加环境
            </el-button>
          </div>
        </template>
        
        <el-alert
          title="环境配置用于隔离不同部署阶段的数据库实例，支持配置独立的 AWS 凭证采集 RDS 性能指标"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        />
        
        <el-table :data="environments" style="width: 100%" :show-overflow-tooltip="false">
          <el-table-column prop="name" label="环境名称" min-width="100" />
          <el-table-column prop="code" label="环境编码" min-width="80" />
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
              <el-tooltip v-if="row.aws_configured" :content="`区域: ${getRegionName(row.aws_region)}`" placement="top">
                <el-tag type="success" size="small">
                  <el-icon><Connection /></el-icon>
                  已配置
                </el-tag>
              </el-tooltip>
              <el-tag v-else type="info" size="small">未配置</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" min-width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status ? 'success' : 'info'" size="small">
                {{ row.status ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="100" />
          <el-table-column label="操作" min-width="100" v-if="canManageEnv" fixed="right" align="center">
            <template #default="{ row }">
              <TableActions :row="row" :actions="envActions" @edit="handleEditEnv" @delete="handleDeleteEnv" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- AWS区域管理内容 -->
    <div v-show="activeTab === 'regions'" class="tab-content">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span>AWS 区域列表</span>
              <el-tag type="success" size="small" style="margin-left: 8px;">启用 {{ enabledRegionCount }} / {{ regions.length }}</el-tag>
            </div>
            <el-button type="primary" @click="handleAddRegion" v-if="canManageRegion">
              <el-icon><Plus /></el-icon>
              添加区域
            </el-button>
          </div>
        </template>
        
        <el-alert
          title="管理 AWS 区域列表，用于环境配置和 RDS 实例管理。禁用区域后不会在下拉列表中显示"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        />
        
        <el-table :data="regions" style="width: 100%" :show-overflow-tooltip="false" v-loading="regionsLoading">
          <el-table-column prop="region_code" label="区域代码" min-width="150">
            <template #default="{ row }">
              <code>{{ row.region_code }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="region_name" label="区域名称" min-width="180" />
          <el-table-column prop="geo_group" label="地理分组" width="100" align="center">
            <template #default="{ row }">
              <el-tag size="small">{{ row.geo_group }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="display_order" label="排序" width="80" align="center" />
          <el-table-column prop="is_enabled" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-switch 
                :model-value="row.is_enabled" 
                @change="handleToggleRegionEnabled(row, $event)"
                :disabled="!canManageRegion"
              />
            </template>
          </el-table-column>
          <el-table-column prop="description" label="描述" min-width="150">
            <template #default="{ row }">
              <span v-if="row.description">{{ row.description }}</span>
              <span v-else style="color: #999;">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" min-width="100" v-if="canManageRegion" fixed="right" align="center">
            <template #default="{ row }">
              <TableActions :row="row" :actions="regionActions" @edit="handleEditRegion" @delete="handleDeleteRegion" />
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 环境编辑对话框 -->
    <el-dialog v-model="envDialog.visible" :title="envDialog.isEdit ? '编辑环境' : '添加环境'" width="600px">
      <el-form :model="envDialog.form" :rules="envDialog.rules" ref="envFormRef" label-width="120px" class="dialog-form">
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="envDialog.form.name" placeholder="请输入环境名称" />
        </el-form-item>
        <el-form-item label="环境编码" prop="code">
          <el-input v-model="envDialog.form.code" placeholder="请输入环境编码（如：development, production）" :disabled="envDialog.isEdit" />
        </el-form-item>
        <el-form-item label="颜色标记" prop="color">
          <el-color-picker v-model="envDialog.form.color" />
        </el-form-item>
        <el-form-item label="需要审批" prop="require_approval">
          <el-switch v-model="envDialog.form.require_approval" />
          <span class="form-hint">开启后，该环境下的实例操作需要审批</span>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="envDialog.form.status" active-text="启用" inactive-text="禁用" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="envDialog.form.description" type="textarea" :rows="2" />
        </el-form-item>
        
        <el-divider content-position="left">
          <el-icon><Cloudy /></el-icon>
          AWS 配置（可选）
        </el-divider>
        
        <el-alert type="warning" :closable="false" show-icon style="margin-bottom: 16px;">
          AWS 凭证用于采集 RDS 实例的 CloudWatch 性能指标，需具有 RDS 和 CloudWatch 只读权限。
        </el-alert>
        
        <el-form-item label="AWS 区域">
          <el-select v-model="envDialog.form.aws_region" placeholder="选择 AWS 区域" style="width: 100%;" :loading="awsRegionsLoading">
            <el-option-group v-for="group in awsRegionGroups" :key="group.geo_group" :label="group.geo_group">
              <el-option v-for="region in group.regions" :key="region.region_code" :label="region.region_name" :value="region.region_code" />
            </el-option-group>
          </el-select>
        </el-form-item>
        
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="Access Key ID">
              <el-input v-model="envDialog.form.aws_access_key_id" placeholder="AKIAIOSFODNN7EXAMPLE" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Secret Key">
              <el-input v-model="envDialog.form.aws_secret_access_key" placeholder="wJalrXUtnFEMI..." show-password />
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
        <el-button @click="envDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitEnv" :loading="envDialog.loading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 区域编辑对话框 -->
    <el-dialog v-model="regionDialog.visible" :title="regionDialog.isEdit ? '编辑区域' : '添加区域'" width="500px">
      <el-form :model="regionDialog.form" :rules="regionDialog.rules" ref="regionFormRef" label-width="100px">
        <el-form-item label="区域代码" prop="region_code">
          <el-input v-model="regionDialog.form.region_code" placeholder="如: ap-southeast-5" :disabled="regionDialog.isEdit" />
        </el-form-item>
        <el-form-item label="区域名称" prop="region_name">
          <el-input v-model="regionDialog.form.region_name" placeholder="如: 亚太地区(曼谷)" />
        </el-form-item>
        <el-form-item label="地理分组" prop="geo_group">
          <el-select v-model="regionDialog.form.geo_group" placeholder="选择分组" style="width: 100%;">
            <el-option label="美国" value="美国" />
            <el-option label="美洲其他" value="美洲其他" />
            <el-option label="欧洲" value="欧洲" />
            <el-option label="亚太" value="亚太" />
            <el-option label="中东" value="中东" />
            <el-option label="非洲" value="非洲" />
            <el-option label="中国" value="中国" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序" prop="display_order">
          <el-input-number v-model="regionDialog.form.display_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="regionDialog.form.is_enabled" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="regionDialog.form.description" type="textarea" :rows="2" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="regionDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitRegion" :loading="regionDialog.loading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Cloudy, Connection, SuccessFilled, CircleCloseFilled, Collection, Location } from '@element-plus/icons-vue'
import { getAwsRegionsGrouped } from '@/api/awsRegions'
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const canManageEnv = computed(() => userStore.hasPermission('environment:create'))
const canManageRegion = computed(() => userStore.hasPermission('environment:update'))

// Tab 状态
const activeTab = ref('environments')

// 操作列配置
const envActions = [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { key: 'delete', label: '删除', event: 'delete', danger: true, primary: false }
]

const regionActions = [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { key: 'delete', label: '删除', event: 'delete', danger: true, primary: false }
]

// ==================== 环境管理 ====================
const environments = ref([])
const awsRegionGroups = ref([])
const awsRegionsLoading = ref(false)
const testingAws = ref(false)
const testResult = ref(null)
const envFormRef = ref(null)

const envDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
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

const canTestAws = computed(() => {
  return envDialog.form.aws_access_key_id && 
         envDialog.form.aws_secret_access_key && 
         envDialog.form.aws_region
})

const getRegionName = (regionCode) => {
  if (!regionCode) return '-'
  for (const group of awsRegionGroups.value) {
    const region = group.regions?.find(r => r.region_code === regionCode)
    if (region) return region.region_name
  }
  return regionCode
}

const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data.items || data
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

const fetchAwsRegions = async () => {
  awsRegionsLoading.value = true
  try {
    const data = await getAwsRegionsGrouped(true)
    awsRegionGroups.value = data
  } catch (error) {
    console.error('获取 AWS 区域失败:', error)
  } finally {
    awsRegionsLoading.value = false
  }
}

const handleAddEnv = () => {
  envDialog.isEdit = false
  envDialog.editingId = null
  envDialog.form = {
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
  envDialog.visible = true
}

const handleEditEnv = (row) => {
  envDialog.isEdit = true
  envDialog.editingId = row.id
  envDialog.form = { 
    id: row.id,
    name: row.name, 
    code: row.code, 
    color: row.color, 
    require_approval: row.require_approval, 
    status: row.status ?? true,
    description: row.description || '',
    aws_region: row.aws_region || '',
    aws_access_key_id: '',
    aws_secret_access_key: ''
  }
  testResult.value = null
  envDialog.visible = true
}

const handleDeleteEnv = async (row) => {
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
    const result = await request.post(`/environments/${envDialog.editingId || 0}/test-aws`, {
      aws_access_key_id: envDialog.form.aws_access_key_id,
      aws_secret_access_key: envDialog.form.aws_secret_access_key,
      aws_region: envDialog.form.aws_region
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

const handleSubmitEnv = async () => {
  if (!envFormRef.value) return
  
  await envFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    envDialog.loading = true
    try {
      const submitData = { ...envDialog.form }
      if (!submitData.aws_access_key_id && !submitData.aws_secret_access_key) {
        delete submitData.aws_access_key_id
        delete submitData.aws_secret_access_key
        delete submitData.aws_region
      }
      
      if (envDialog.isEdit) {
        await request.put(`/environments/${envDialog.editingId}`, submitData)
        ElMessage.success('更新成功')
      } else {
        await request.post('/environments', submitData)
        ElMessage.success('添加成功')
      }
      envDialog.visible = false
      fetchEnvironments()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      envDialog.loading = false
    }
  })
}

// ==================== AWS 区域管理 ====================
const regions = ref([])
const regionsLoading = ref(false)
const regionFormRef = ref(null)

const enabledRegionCount = computed(() => regions.value.filter(r => r.is_enabled).length)

const regionDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  editingId: null,
  form: {
    region_code: '',
    region_name: '',
    geo_group: '亚太',
    display_order: 50,
    is_enabled: true,
    description: ''
  },
  rules: {
    region_code: [{ required: true, message: '请输入区域代码', trigger: 'blur' }],
    region_name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
    geo_group: [{ required: true, message: '请选择地理分组', trigger: 'change' }]
  }
})

const fetchRegions = async () => {
  regionsLoading.value = true
  try {
    const data = await request.get('/aws-regions', { params: { enabled_only: false } })
    regions.value = data || []
  } catch (error) {
    console.error('获取区域列表失败:', error)
    ElMessage.error('获取区域列表失败')
  } finally {
    regionsLoading.value = false
  }
}

const handleAddRegion = () => {
  regionDialog.isEdit = false
  regionDialog.editingId = null
  regionDialog.form = {
    region_code: '',
    region_name: '',
    geo_group: '亚太',
    display_order: 50,
    is_enabled: true,
    description: ''
  }
  regionDialog.visible = true
}

const handleEditRegion = (row) => {
  regionDialog.isEdit = true
  regionDialog.editingId = row.id
  regionDialog.form = {
    region_code: row.region_code,
    region_name: row.region_name,
    geo_group: row.geo_group,
    display_order: row.display_order,
    is_enabled: row.is_enabled,
    description: row.description || ''
  }
  regionDialog.visible = true
}

const handleToggleRegionEnabled = async (row, value) => {
  try {
    await request.put(`/aws-regions/${row.id}`, { is_enabled: value })
    row.is_enabled = value
    ElMessage.success(value ? '已启用' : '已禁用')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const handleDeleteRegion = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除区域 "${row.region_name}" 吗？`, '警告', { type: 'warning' })
    await request.delete(`/aws-regions/${row.id}`)
    ElMessage.success('删除成功')
    fetchRegions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleSubmitRegion = async () => {
  if (!regionFormRef.value) return
  
  await regionFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    regionDialog.loading = true
    try {
      if (regionDialog.isEdit) {
        await request.put(`/aws-regions/${regionDialog.editingId}`, regionDialog.form)
        ElMessage.success('更新成功')
      } else {
        await request.post('/aws-regions', regionDialog.form)
        ElMessage.success('添加成功')
      }
      regionDialog.visible = false
      fetchRegions()
      // 同时刷新环境管理中使用的区域数据
      fetchAwsRegions()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      regionDialog.loading = false
    }
  })
}

// Tab 切换时加载数据
const handleTabChange = (tab) => {
  if (tab === 'regions' && regions.value.length === 0) {
    fetchRegions()
  }
}

onMounted(() => {
  fetchEnvironments()
  fetchAwsRegions()
})
</script>

<style lang="scss" scoped>
.environment-config-page {
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
  
  code {
    background: #f5f7fa;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }
}
</style>
