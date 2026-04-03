<template>
  <div class="ai-models-page">
    <!-- 顶部说明 -->
    <el-alert type="info" :closable="false" show-icon class="info-alert">
      <template #title>
        配置 AI 模型作为底座，然后将模型关联到具体的业务场景。
        支持多模型配置，不同场景可使用不同的模型。
      </template>
    </el-alert>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="main-tabs">
      <el-tab-pane label="场景配置" name="scenes">
        <div class="toolbar">
          <el-button @click="fetchSceneConfigs">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
        
        <el-table :data="sceneConfigs" v-loading="sceneLoading" stripe>
          <el-table-column prop="scene_label" label="场景" width="150">
            <template #default="{ row }">
              <el-tag type="primary">{{ row.scene_label }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="关联模型" min-width="200">
            <template #default="{ row }">
              <div v-if="row.model_config" class="model-info">
                <span class="model-name">{{ row.model_config.name }}</span>
                <el-tag 
                  :type="row.model_config.provider === 'doubao' ? 'primary' : 'success'" 
                  size="small"
                >
                  {{ row.model_config.provider }}
                </el-tag>
                <el-tag 
                  v-if="!row.model_config.is_enabled" 
                  type="danger" 
                  size="small"
                >
                  已禁用
                </el-tag>
              </div>
              <el-text v-else type="warning">未配置</el-text>
            </template>
          </el-table-column>
          <el-table-column prop="is_enabled" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_enabled ? 'success' : 'danger'">
                {{ row.is_enabled ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button type="primary" link @click="handleEditScene(row)">
                配置
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="模型底座" name="models">
        <div class="toolbar">
          <el-button type="primary" @click="handleAdd" v-if="isAdmin">
            <el-icon><Plus /></el-icon>新增模型
          </el-button>
          <el-button @click="fetchList">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>

        <el-table :data="modelList" v-loading="loading" stripe>
          <el-table-column prop="name" label="配置名称" min-width="150" />
          <el-table-column prop="provider_label" label="提供商" width="130">
            <template #default="{ row }">
              <el-tag :type="getProviderTagType(row.provider)" effect="plain">
                {{ row.provider_label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="model_name" label="模型标识" min-width="200">
            <template #default="{ row }">
              <el-tooltip :content="`API: ${row.base_url}`" placement="top">
                <span class="model-id">{{ row.model_name }}</span>
              </el-tooltip>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="80" align="center" />
          <el-table-column prop="is_enabled" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-switch
                v-model="row.is_enabled"
                :disabled="!isAdmin"
                @change="toggleEnabled(row)"
              />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-btns">
                <el-button type="primary" text size="small" @click="handleEdit(row)">编辑</el-button>
                <el-button type="success" text size="small" @click="handleTest(row)">测试</el-button>
                <el-button v-if="isAdmin" type="danger" text size="small" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 场景配置对话框 -->
    <el-dialog v-model="sceneDialog.visible" title="配置场景" width="500px">
      <el-form :model="sceneForm" label-width="100px">
        <el-form-item label="场景">
          <el-tag type="primary">{{ sceneForm.scene_label }}</el-tag>
        </el-form-item>
        <el-form-item label="关联模型" required>
          <el-select 
            v-model="sceneForm.model_config_id" 
            style="width: 100%"
            placeholder="请选择关联模型"
            clearable
          >
            <el-option
              v-for="model in enabledModels"
              :key="model.id"
              :label="`${model.name} (${model.provider_label})`"
              :value="model.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="是否启用">
          <el-switch v-model="sceneForm.is_enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="sceneDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveScene" :loading="sceneDialog.submitting">
          保存
        </el-button>
      </template>
    </el-dialog>

    <!-- 新增/编辑模型对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑模型' : '新增模型'"
      width="650px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="如：豆包生产模型" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="提供商" prop="provider">
              <el-select v-model="form.provider" style="width: 100%" @change="handleProviderChange">
                <el-option
                  v-for="p in providers"
                  :key="p.value"
                  :label="p.label"
                  :value="p.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="模型类型" prop="model_type">
              <el-select v-model="form.model_type" style="width: 100%">
                <el-option label="对话模型 (Chat)" value="chat" />
                <el-option label="补全模型 (Completion)" value="completion" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">连接配置</el-divider>
        <el-form-item label="API 地址" prop="base_url">
          <el-input v-model="form.base_url" placeholder="https://api.example.com/v1" />
        </el-form-item>
        <el-form-item label="API 密钥" prop="api_key">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            placeholder="留空则不修改"
          />
          <div class="form-hint" v-if="dialog.isEdit && form.api_key_masked">
            当前密钥：{{ form.api_key_masked }}
          </div>
        </el-form-item>
        <el-form-item label="模型名称" prop="model_name">
          <div class="model-name-select">
            <el-select
              v-model="form.model_name"
              filterable
              allow-create
              default-first-option
              placeholder="选择或输入模型名称"
              style="width: 100%"
            >
              <el-option
                v-for="model in currentProviderModels"
                :key="model.model_id"
                :label="model.model_name"
                :value="model.model_id"
              />
            </el-select>
            <el-button 
              type="primary" 
              link 
              @click="handleRefreshModels"
              :loading="refreshingModels"
              title="从提供商刷新模型列表"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>
          <div class="form-hint" v-if="currentProviderModels.length === 0">
            暂无可用模型列表，请手动输入或点击刷新按钮
          </div>
        </el-form-item>

        <el-divider content-position="left">参数配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大 Token">
              <el-input-number v-model="form.max_tokens" :min="1" :max="128000" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="form.timeout" :min="1" :max="300" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="Temperature">
              <el-input-number v-model="form.temperature" :min="0" :max="2" :step="0.1" :precision="1" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="100" style="width: 100%" />
              <div class="form-hint">数值越大优先级越高</div>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="是否启用">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="描述">
          <el-input 
            v-model="form.description" 
            type="textarea" 
            :rows="2" 
            placeholder="模型配置的描述说明（可选）" 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog v-model="testDialog.visible" title="测试模型连接" width="500px">
      <el-form label-width="100px">
        <el-form-item label="配置名称">
          <span>{{ testDialog.modelName }}</span>
        </el-form-item>
        <el-form-item label="测试提示词">
          <el-input
            v-model="testDialog.prompt"
            type="textarea"
            :rows="3"
            placeholder="输入测试提示词"
          />
        </el-form-item>
        <template v-if="testDialog.result">
          <el-form-item label="测试结果">
            <el-tag :type="testDialog.result.success ? 'success' : 'danger'">
              {{ testDialog.result.success ? '成功' : '失败' }}
            </el-tag>
            <span style="margin-left: 10px;">耗时：{{ testDialog.result.latency_ms }} ms</span>
          </el-form-item>
          <el-form-item v-if="testDialog.result.response" label="响应内容">
            <el-input
              :model-value="testDialog.result.response"
              type="textarea"
              :rows="4"
              readonly
            />
          </el-form-item>
          <el-form-item v-if="testDialog.result.error" label="错误信息">
            <el-input
              :model-value="testDialog.result.error"
              type="textarea"
              :rows="2"
              readonly
            />
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="testDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="executeTest" :loading="testDialog.loading">
          测试
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { aiModelsApi } from '@/api/aiModels'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const activeTab = ref('scenes')

// ========== 场景配置 ==========
const sceneLoading = ref(false)
const sceneConfigs = ref([])

const sceneDialog = reactive({
  visible: false,
  submitting: false
})

const sceneForm = reactive({
  scene: '',
  scene_label: '',
  model_config_id: null,
  is_enabled: true
})

const fetchSceneConfigs = async () => {
  sceneLoading.value = true
  try {
    sceneConfigs.value = await aiModelsApi.getSceneConfigs()
  } catch (error) {
    console.error('获取场景配置失败:', error)
    ElMessage.error('获取场景配置失败')
  } finally {
    sceneLoading.value = false
  }
}

const handleEditScene = (row) => {
  sceneForm.scene = row.scene
  sceneForm.scene_label = row.scene_label
  // 确保 model_config_id 是数字类型，与 el-select 的 value 类型匹配
  sceneForm.model_config_id = row.model_config_id ? Number(row.model_config_id) : null
  sceneForm.is_enabled = row.is_enabled
  // 如果模型列表未加载，先加载
  if (modelList.value.length === 0) {
    fetchList()
  }
  sceneDialog.visible = true
}

const handleSaveScene = async () => {
  if (!sceneForm.model_config_id) {
    ElMessage.warning('请选择关联模型')
    return
  }

  sceneDialog.submitting = true
  try {
    await aiModelsApi.updateSceneConfig(sceneForm.scene, {
      model_config_id: sceneForm.model_config_id,
      is_enabled: sceneForm.is_enabled
    })
    ElMessage.success('保存成功')
    sceneDialog.visible = false
    fetchSceneConfigs()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    sceneDialog.submitting = false
  }
}

// ========== 模型配置 ==========
const loading = ref(false)
const modelList = ref([])
const providers = ref([])
const availableModels = ref({})
const refreshingModels = ref(false)

const formRef = ref()
const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false
})

const form = reactive({
  name: '',
  provider: 'doubao',
  base_url: '',
  api_key: '',
  api_key_masked: '',
  model_name: '',
  model_type: 'chat',
  max_tokens: 4096,
  temperature: 0.7,
  timeout: 30,
  is_enabled: true,
  priority: 0,
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  base_url: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

const testDialog = reactive({
  visible: false,
  modelId: null,
  modelName: '',
  prompt: '你好，请回复"测试成功"',
  loading: false,
  result: null
})

const enabledModels = computed(() => modelList.value.filter(m => m.is_enabled))

const currentProviderModels = computed(() => {
  const models = availableModels.value[form.provider] || []
  return models
})

const getProviderTagType = (provider) => {
  const types = {
    'doubao': 'primary',
    'openai': 'success',
    'ollama': 'warning',
    'custom': 'info'
  }
  return types[provider] || 'info'
}

const fetchList = async () => {
  loading.value = true
  try {
    modelList.value = await aiModelsApi.getList()
  } catch (error) {
    console.error('获取列表失败:', error)
    ElMessage.error('获取模型配置列表失败')
  } finally {
    loading.value = false
  }
}

const fetchProviders = async () => {
  try {
    providers.value = await aiModelsApi.getProviders()
  } catch (error) {
    console.error('获取提供商失败:', error)
  }
}

const fetchAvailableModels = async () => {
  try {
    const result = await aiModelsApi.getAvailableModels()
    availableModels.value = result.by_provider || {}
  } catch (error) {
    console.error('获取可用模型失败:', error)
  }
}

const handleRefreshModels = async () => {
  refreshingModels.value = true
  try {
    const result = await aiModelsApi.refreshAvailableModels()
    if (result.errors && result.errors.length > 0) {
      ElMessage.warning(`部分刷新失败: ${result.errors.join(', ')}`)
    } else {
      ElMessage.success(`刷新成功: ${JSON.stringify(result.refreshed)}`)
    }
    await fetchAvailableModels()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '刷新失败')
  } finally {
    refreshingModels.value = false
  }
}

const handleProviderChange = (provider) => {
  const defaults = {
    'doubao': 'https://integration.coze.cn/api/v3',
    'openai': 'https://api.openai.com/v1',
    'ollama': 'http://localhost:11434/v1'
  }
  if (defaults[provider] && !form.base_url) {
    form.base_url = defaults[provider]
  }
  
  // 自动填充模型名称为该提供商的第一个可用模型
  const models = availableModels.value[provider] || []
  if (models.length > 0 && !form.model_name) {
    // 优先选择推荐的模型，否则选择第一个
    const recommendedModel = models.find(m => m.is_recommended)
    form.model_name = recommendedModel ? recommendedModel.model_id : models[0].model_id
  }
}

const handleAdd = () => {
  dialog.isEdit = false
  resetFormData()
  dialog.visible = true
}

const handleEdit = async (row) => {
  dialog.isEdit = true
  Object.assign(form, {
    id: row.id,
    name: row.name,
    provider: row.provider,
    base_url: row.base_url,
    api_key: '',
    api_key_masked: row.api_key_masked,
    model_name: row.model_name,
    model_type: row.model_type,
    max_tokens: row.max_tokens,
    temperature: row.temperature,
    timeout: row.timeout,
    is_enabled: row.is_enabled,
    priority: row.priority,
    description: row.description || ''
  })
  // 加载可用模型列表，确保模型名称选择器能正常显示
  await fetchAvailableModels()
  dialog.visible = true
}

const resetFormData = () => {
  Object.assign(form, {
    id: null,
    name: '',
    provider: 'doubao',
    base_url: '',
    api_key: '',
    api_key_masked: '',
    model_name: '',
    model_type: 'chat',
    max_tokens: 4096,
    temperature: 0.7,
    timeout: 30,
    is_enabled: true,
    priority: 0,
    description: ''
  })
}

const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  dialog.submitting = true
  try {
    const data = { ...form }
    if (!data.api_key) delete data.api_key

    if (dialog.isEdit) {
      await aiModelsApi.update(form.id, data)
      ElMessage.success('更新成功')
    } else {
      await aiModelsApi.create(data)
      ElMessage.success('创建成功')
    }

    dialog.visible = false
    fetchList()
    fetchSceneConfigs()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    dialog.submitting = false
  }
}

const toggleEnabled = async (row) => {
  try {
    await aiModelsApi.update(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(row.is_enabled ? '已启用' : '已禁用')
    fetchSceneConfigs()
  } catch (error) {
    row.is_enabled = !row.is_enabled
    ElMessage.error('操作失败')
  }
}

const handleTest = (row) => {
  testDialog.modelId = row.id
  testDialog.modelName = row.name
  testDialog.result = null
  testDialog.visible = true
}

const executeTest = async () => {
  if (!testDialog.prompt.trim()) {
    ElMessage.warning('请输入测试提示词')
    return
  }

  testDialog.loading = true
  testDialog.result = null
  try {
    testDialog.result = await aiModelsApi.test(testDialog.modelId, testDialog.prompt)
  } catch (error) {
    testDialog.result = {
      success: false,
      error: error.response?.data?.detail || '测试失败',
      latency_ms: 0
    }
  } finally {
    testDialog.loading = false
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除 "${row.name}"？`, '确认删除', { type: 'warning' })
    await aiModelsApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

onMounted(() => {
  fetchSceneConfigs()
  fetchList()
  fetchProviders()
  fetchAvailableModels()
})
</script>

<style scoped>
.ai-models-page {
  padding: 20px;
}

.info-alert {
  margin-bottom: 20px;
}

.main-tabs {
  margin-bottom: 16px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
}

.model-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name {
  font-weight: 500;
}

.model-id {
  color: var(--el-text-color-primary);
  cursor: pointer;
}

.action-btns {
  display: flex;
  justify-content: center;
  gap: 4px;
}

.action-btns .el-button {
  padding: 4px 8px;
}

.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.model-name-select {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-name-select .el-select {
  flex: 1;
}
</style>
