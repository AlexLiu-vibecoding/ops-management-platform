<template>
  <div class="notification-templates-page">
    <!-- 筛选条件 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="通知类型">
          <el-select v-model="filters.notification_type" placeholder="全部类型" clearable style="width: 150px">
            <el-option label="审批通知" value="approval" />
            <el-option label="告警通知" value="alert" />
            <el-option label="定时任务" value="scheduled_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.is_enabled" placeholder="全部状态" clearable style="width: 100px">
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadTemplates">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="primary" @click="handleCreate">
            <el-icon><Plus /></el-icon>
            新建模板
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 模板列表 -->
    <el-card shadow="never" class="table-card">
      <el-table 
        :data="templates" 
        style="width: 100%" 
        v-loading="loading"
      >
        <el-table-column prop="name" label="模板名称" min-width="150">
          <template #default="{ row }">
            <div class="template-name">
              <span>{{ row.name }}</span>
              <el-tag v-if="row.is_default" type="success" size="small" class="default-tag">默认</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150">
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="notification_type" label="通知类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.notification_type)" size="small">
              {{ getTypeName(row.notification_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sub_type" label="细分类型" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.sub_type">{{ row.sub_type }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.updated_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click="handlePreview(row)">
              预览
            </el-button>
            <el-button type="primary" text size="small" @click="handleEdit(row)">
              编辑
            </el-button>
            <el-popconfirm
              v-if="!row.is_default"
              title="确定删除这个模板吗？"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button type="danger" text size="small">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadTemplates"
          @current-change="loadTemplates"
        />
      </div>
    </el-card>

    <!-- 编辑/新建对话框 -->
    <el-dialog
      v-model="dialog.visible"
      :title="dialog.isEdit ? '编辑模板' : '新建模板'"
      width="800px"
      destroy-on-close
    >
      <el-form 
        ref="formRef"
        :model="dialog.form" 
        :rules="formRules" 
        label-width="120px"
        class="template-form"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="模板名称" prop="name">
              <el-input v-model="dialog.form.name" placeholder="请输入模板名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="通知类型" prop="notification_type">
              <el-select 
                v-model="dialog.form.notification_type" 
                placeholder="请选择通知类型"
                style="width: 100%"
                @change="handleTypeChange"
              >
                <el-option label="审批通知" value="approval" />
                <el-option label="告警通知" value="alert" />
                <el-option label="定时任务" value="scheduled_task" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="细分类型">
              <el-input 
                v-model="dialog.form.sub_type" 
                placeholder="如: DDL/DML/critical"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="描述">
              <el-input v-model="dialog.form.description" placeholder="请输入描述" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="标题模板" prop="title_template">
          <el-input v-model="dialog.form.title_template" placeholder="请输入标题模板" />
        </el-form-item>

        <el-form-item label="内容模板" prop="content_template">
          <el-input
            v-model="dialog.form.content_template"
            type="textarea"
            :rows="12"
            placeholder="请输入内容模板 (Markdown格式)"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="状态">
              <el-switch v-model="dialog.form.is_enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="设为默认">
              <el-switch v-model="dialog.form.is_default" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>

      <div class="template-hints">
        <h4>可用变量</h4>
        <div v-if="availableVariables.length > 0" class="variables-grid">
          <el-tag 
            v-for="var in availableVariables" 
            :key="var.name"
            class="variable-tag"
            @click="insertVariable(var.name)"
            type="info"
          >
            <span class="var-name">{ {{ var.name }} }</span>
            <el-tooltip :content="var.description">
              <el-icon class="var-info"><InfoFilled /></el-icon>
            </el-tooltip>
          </el-tag>
        </div>
        <span v-else class="text-gray-400">请先选择通知类型</span>
      </div>

      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSave" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialog.visible"
      title="模板预览"
      width="600px"
    >
      <div class="preview-content">
        <div class="preview-title">{{ previewDialog.data?.title_template }}</div>
        <pre class="preview-body">{{ previewMarkdown }}</pre>
      </div>
      <template #footer>
        <el-button @click="previewDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { formatTime } from '@/utils/format'

// 筛选条件
const filters = reactive({
  notification_type: '',
  is_enabled: null
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 列表数据
const templates = ref([])
const loading = ref(false)

// 对话框
const dialog = reactive({
  visible: false,
  isEdit: false,
  form: {
    name: '',
    description: '',
    notification_type: '',
    sub_type: '',
    title_template: '',
    content_template: '',
    variables: [],
    is_enabled: true,
    is_default: false
  }
})

const formRef = ref(null)
const saving = ref(false)

// 预览对话框
const previewDialog = reactive({
  visible: false,
  data: null
})

// 表单验证
const formRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  notification_type: [{ required: true, message: '请选择通知类型', trigger: 'change' }],
  title_template: [{ required: true, message: '请输入标题模板', trigger: 'blur' }],
  content_template: [{ required: true, message: '请输入内容模板', trigger: 'blur' }]
}

// 可用变量
const availableVariables = computed(() => {
  if (dialog.form.variables && Array.isArray(dialog.form.variables)) {
    return dialog.form.variables
  }
  return []
})

// 预览的 Markdown
const previewMarkdown = computed(() => {
  if (!previewDialog.data) return ''
  return previewDialog.data.content_template
})

// 加载模板列表
const loadTemplates = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (filters.notification_type) {
      params.notification_type = filters.notification_type
    }
    if (filters.is_enabled !== null) {
      params.is_enabled = filters.is_enabled
    }

    const res = await request.get('/notification-templates', { params })
    if (res.code === 0) {
      templates.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error('加载模板列表失败:', error)
    ElMessage.error('加载模板列表失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.notification_type = ''
  filters.is_enabled = null
  pagination.page = 1
  loadTemplates()
}

// 新建模板
const handleCreate = () => {
  dialog.isEdit = false
  dialog.visible = true
  dialog.form = {
    name: '',
    description: '',
    notification_type: '',
    sub_type: '',
    title_template: '',
    content_template: '',
    variables: [],
    is_enabled: true,
    is_default: false
  }
}

// 编辑模板
const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.visible = true
  dialog.form = { ...row }
}

// 预览模板
const handlePreview = (row) => {
  previewDialog.data = row
  previewDialog.visible = true
}

// 类型变化
const handleTypeChange = (type) => {
  // 获取该类型的默认模板和变量
  request.get(`/notification-templates/default/${type}`).then(res => {
    if (res.code === 0) {
      dialog.form.title_template = res.data.title_template
      dialog.form.content_template = res.data.content_template
      dialog.form.variables = res.data.variables
    }
  })
}

// 插入变量
const insertVariable = (varName) => {
  const varStr = `{${varName}}`
  dialog.form.content_template += varStr
}

// 保存模板
const handleSave = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      let res
      if (dialog.isEdit) {
        res = await request.put(`/notification-templates/${dialog.form.id}`, dialog.form)
      } else {
        res = await request.post('/notification-templates', dialog.form)
      }
      
      if (res.code === 0) {
        ElMessage.success('保存成功')
        dialog.visible = false
        loadTemplates()
      } else {
        ElMessage.error(res.message || '保存失败')
      }
    } catch (error) {
      console.error('保存模板失败:', error)
      ElMessage.error('保存模板失败')
    } finally {
      saving.value = false
    }
  })
}

// 删除模板
const handleDelete = async (row) => {
  try {
    const res = await request.delete(`/notification-templates/${row.id}`)
    if (res.code === 0) {
      ElMessage.success('删除成功')
      loadTemplates()
    } else {
      ElMessage.error(res.message || '删除失败')
    }
  } catch (error) {
    console.error('删除模板失败:', error)
    ElMessage.error('删除模板失败')
  }
}

// 类型映射
const getTypeTag = (type) => {
  const map = {
    'approval': 'primary',
    'alert': 'danger',
    'scheduled_task': 'warning'
  }
  return map[type] || ''
}

const getTypeName = (type) => {
  const map = {
    'approval': '审批通知',
    'alert': '告警通知',
    'scheduled_task': '定时任务'
  }
  return map[type] || type
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.notification-templates-page {
  padding: 20px;
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.table-card {
  margin-bottom: 20px;
}

.template-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.default-tag {
  font-size: 12px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.template-form {
  margin-bottom: 20px;
}

.template-hints {
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 20px;
  margin-top: 20px;
}

.template-hints h4 {
  margin: 0 0 10px 0;
  color: var(--el-text-color-regular);
  font-size: 14px;
}

.variables-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.variable-tag {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 4px 8px;
}

.variable-tag:hover {
  background-color: var(--el-color-primary-light-9);
}

.var-name {
  font-family: monospace;
}

.var-info {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.text-gray-400 {
  color: var(--el-text-color-placeholder);
}

.preview-content {
  background-color: var(--el-fill-color-light);
  padding: 20px;
  border-radius: 4px;
}

.preview-title {
  font-size: 18px;
  font-weight: bold;
  margin-bottom: 16px;
  color: var(--el-text-color-primary);
}

.preview-body {
  color: var(--el-text-color-regular);
  line-height: 1.6;
  white-space: pre-wrap;
  background-color: var(--el-fill-color-lighter);
  padding: 12px;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  margin: 0;
}
</style>
