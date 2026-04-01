<template>
  <div class="ai-models-page">
    <!-- 顶部说明 -->
    <el-alert type="info" :closable="false" show-icon class="info-alert">
      <template #title>
        配置 AI 模型通道，支持多模型调用、主备切换和交叉验证。
        系统会按优先级选择可用模型，确保 AI 分析功能的稳定性。
      </template>
    </el-alert>

    <!-- 操作栏 -->
    <div class="toolbar">
      <el-button type="primary" @click="handleAdd" v-if="isAdmin">
        <el-icon><Plus /></el-icon>新增模型配置
      </el-button>
      <el-button @click="fetchList">
        <el-icon><Refresh /></el-icon>刷新
      </el-button>
    </div>

    <!-- 模型列表 -->
    <el-table :data="modelList" v-loading="loading" stripe>
      <el-table-column prop="name" label="配置名称" min-width="150">
        <template #default="{ row }">
          <div class="model-name">
            <span>{{ row.name }}</span>
            <el-tag v-if="row.is_default" type="success" size="small">默认</el-tag>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="provider_label" label="提供商" width="130">
        <template #default="{ row }">
          <el-tag :type="getProviderTagType(row.provider)" effect="plain">
            {{ row.provider_label }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="model_name" label="模型" min-width="180">
        <template #default="{ row }">
          <el-tooltip :content="row.base_url" placement="top">
            <span class="model-info">{{ row.model_name }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="use_case_labels" label="使用场景" min-width="150">
        <template #default="{ row }">
          <el-tag v-for="uc in row.use_case_labels" :key="uc" size="small" class="use-case-tag">
            {{ uc }}
          </el-tag>
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
          <TableActions :row="row" :actions="getActions(row)" :max-primary="2"
            @edit="handleEdit(row)" @test="handleTest(row)"
            @setDefault="handleSetDefault(row)" @delete="handleDelete(row)" />
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑配置' : '新增配置'"
      width="650px"
      @close="resetForm"
    >
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="配置名称" prop="name">
              <el-input v-model="form.name" placeholder="如：豆包生产通道" />
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

        <!-- 连接配置 -->
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
          <el-input v-model="form.model_name" placeholder="gpt-4o / qwen2.5:7b" />
        </el-form-item>

        <!-- 参数配置 -->
        <el-divider content-position="left">参数配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="最大 Token">
              <el-input-number v-model="form.max_tokens" :min="1" :max="128000" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="Temperature">
              <el-slider v-model="form.temperature" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="form.timeout" :min="1" :max="300" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-input-number v-model="form.priority" :min="0" :max="100" style="width: 100%" />
              <div class="form-hint">数值越大优先级越高</div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 高级配置 -->
        <el-divider content-position="left">高级配置</el-divider>
        <el-form-item label="使用场景">
          <el-checkbox-group v-model="form.use_cases">
            <el-checkbox v-for="uc in useCases" :key="uc.value" :label="uc.value">
              {{ uc.label }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="可选描述" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="是否启用">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认">
              <el-switch v-model="form.is_default" />
            </el-form-item>
          </el-col>
        </el-row>
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
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const loading = ref(false)
const modelList = ref([])
const providers = ref([])
const useCases = ref([])

// 对话框
const formRef = ref()
const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false
})

// 表单
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
  is_default: false,
  priority: 0,
  use_cases: ['alert_analysis'],
  description: ''
})

// 表单校验规则
const rules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  provider: [{ required: true, message: '请选择提供商', trigger: 'change' }],
  base_url: [{ required: true, message: '请输入 API 地址', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

// 测试对话框
const testDialog = reactive({
  visible: false,
  modelId: null,
  modelName: '',
  prompt: '你好，请回复"测试成功"',
  loading: false,
  result: null
})

// 获取提供商标签类型
const getProviderTagType = (provider) => {
  const types = {
    'doubao': 'primary',
    'openai': 'success',
    'ollama': 'warning',
    'custom': 'info'
  }
  return types[provider] || 'info'
}

// 获取操作按钮
const getActions = (row) => {
  const actions = [
    { key: 'test', label: '测试', event: 'test', primary: true },
    { key: 'edit', label: '编辑', event: 'edit', primary: true }
  ]
  if (!row.is_default) {
    actions.push({ key: 'setDefault', label: '设为默认', event: 'setDefault' })
  }
  if (!row.is_default && isAdmin.value) {
    actions.push({ key: 'delete', label: '删除', event: 'delete', danger: true })
  }
  return actions.filter(a => a.primary || isAdmin.value)
}

// 获取列表
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

// 获取基础数据
const fetchBaseData = async () => {
  try {
    const [providersRes, useCasesRes] = await Promise.all([
      aiModelsApi.getProviders(),
      aiModelsApi.getUseCases()
    ])
    providers.value = providersRes
    useCases.value = useCasesRes
  } catch (error) {
    console.error('获取基础数据失败:', error)
  }
}

// 提供商变更
const handleProviderChange = (provider) => {
  // 根据提供商设置默认 API 地址
  const defaults = {
    'doubao': 'https://ark.cn-beijing.volces.com/api/v3',
    'openai': 'https://api.openai.com/v1',
    'ollama': 'http://localhost:11434/v1'
  }
  if (defaults[provider] && !form.base_url) {
    form.base_url = defaults[provider]
  }
}

// 新增
const handleAdd = () => {
  dialog.isEdit = false
  resetFormData()
  dialog.visible = true
}

// 编辑
const handleEdit = (row) => {
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
    is_default: row.is_default,
    priority: row.priority,
    use_cases: row.use_cases || [],
    description: row.description || ''
  })
  dialog.visible = true
}

// 重置表单
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
    is_default: false,
    priority: 0,
    use_cases: ['alert_analysis'],
    description: ''
  })
}

// 重置表单
const resetForm = () => {
  formRef.value?.resetFields()
  resetFormData()
}

// 提交
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
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    dialog.submitting = false
  }
}

// 切换启用状态
const toggleEnabled = async (row) => {
  try {
    await aiModelsApi.update(row.id, { is_enabled: row.is_enabled })
    ElMessage.success(row.is_enabled ? '已启用' : '已禁用')
  } catch (error) {
    row.is_enabled = !row.is_enabled
    ElMessage.error('操作失败')
  }
}

// 测试
const handleTest = (row) => {
  testDialog.modelId = row.id
  testDialog.modelName = row.name
  testDialog.result = null
  testDialog.visible = true
}

// 执行测试
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

// 设为默认
const handleSetDefault = async (row) => {
  try {
    await ElMessageBox.confirm(`确定将 "${row.name}" 设为默认模型？`, '确认')
    await aiModelsApi.setDefault(row.id)
    ElMessage.success('已设为默认模型')
    fetchList()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }
}

// 删除
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
  fetchList()
  fetchBaseData()
})
</script>

<style scoped>
.ai-models-page {
  padding: 20px;
}

.info-alert {
  margin-bottom: 20px;
}

.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 10px;
}

.model-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.model-info {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.use-case-tag {
  margin-right: 4px;
}

.form-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}
</style>
