<template>
  <div class="scripts-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>脚本管理</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新建脚本
          </el-button>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-select v-model="filters.script_type" placeholder="脚本类型" clearable style="width: 150px;">
          <el-option label="Python" value="python" />
          <el-option label="Bash" value="bash" />
          <el-option label="SQL" value="sql" />
        </el-select>
        <el-input v-model="filters.search" placeholder="搜索脚本名称或描述" clearable style="width: 250px;" @keyup.enter="fetchScripts" />
        <el-button type="primary" @click="fetchScripts">搜索</el-button>
      </div>
      
      <!-- 脚本列表 -->
      <el-table :data="scripts" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="脚本名称" min-width="100" show-overflow-tooltip />
        <el-table-column prop="script_type" label="类型" width="70" align="center">
          <template #default="{ row }">
            <el-tag :type="getScriptTypeTag(row.script_type)" size="small">
              {{ row.script_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="100" show-overflow-tooltip />
        <el-table-column prop="is_enabled" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_public" label="公开" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_public" type="warning" size="small">是</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="80" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleExecute(row)">执行</el-button>
              <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="primary" size="small" @click="handleDuplicate(row)">复制</el-button>
              <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchScripts"
          @current-change="fetchScripts"
        />
      </div>
    </el-card>
    
    <!-- 新建/编辑脚本对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑脚本' : '新建脚本'" width="900px" :close-on-click-modal="false">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="脚本名称" prop="name">
              <el-input v-model="dialog.form.name" placeholder="请输入脚本名称" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="脚本类型" prop="script_type">
              <el-select v-model="dialog.form.script_type" style="width: 100%;">
                <el-option label="Python" value="python" />
                <el-option label="Bash" value="bash" />
                <el-option label="SQL" value="sql" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="脚本内容" prop="content">
          <el-input
            v-model="dialog.form.content"
            type="textarea"
            :rows="15"
            placeholder="请输入脚本内容"
            class="code-editor"
          />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" placeholder="脚本描述" />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="超时时间">
              <el-input-number v-model="dialog.form.timeout" :min="1" :max="3600" />
              <span style="margin-left: 5px;">秒</span>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最大重试">
              <el-input-number v-model="dialog.form.max_retries" :min="0" :max="10" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="公开">
              <el-switch v-model="dialog.form.is_public" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="标签">
          <el-input v-model="dialog.form.tags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        
        <!-- 通知配置 -->
        <el-divider content-position="left">通知配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="成功通知">
              <el-switch v-model="dialog.form.notify_on_success" />
              <span class="hint">执行成功时发送通知</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="失败通知">
              <el-switch v-model="dialog.form.notify_on_failure" />
              <span class="hint">执行失败时发送通知</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="通知通道">
          <el-select
            v-model="dialog.form.notify_channels"
            multiple
            placeholder="选择通知通道"
            style="width: 100%;"
          >
            <el-option
              v-for="channel in notificationChannels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id.toString()"
            />
          </el-select>
          <div class="hint">执行完成后向选中的通道发送通知</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">
          {{ dialog.isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 执行脚本对话框 -->
    <el-dialog v-model="execDialog.visible" title="执行脚本" width="700px">
      <el-form label-width="100px">
        <el-form-item label="脚本">
          <span>{{ execDialog.scriptName }}</span>
        </el-form-item>
        <el-form-item label="参数">
          <el-input
            v-model="execDialog.params"
            type="textarea"
            :rows="5"
            placeholder="JSON格式的参数，如: {&quot;key&quot;: &quot;value&quot;}"
          />
        </el-form-item>
        <el-form-item label="执行方式">
          <el-radio-group v-model="execDialog.async_exec">
            <el-radio :value="true">异步执行</el-radio>
            <el-radio :value="false">同步执行</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="execDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitExecute" :loading="execDialog.loading">
          执行
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 执行结果对话框 -->
    <el-dialog v-model="resultDialog.visible" title="执行结果" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(resultDialog.data?.status)">
            {{ resultDialog.data?.status }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="执行时长">
          {{ resultDialog.data?.duration?.toFixed(2) || 0 }} 秒
        </el-descriptions-item>
      </el-descriptions>
      
      <div class="output-section" v-if="resultDialog.data?.output">
        <h4>标准输出</h4>
        <pre class="output-box">{{ resultDialog.data?.output }}</pre>
      </div>
      
      <div class="output-section error" v-if="resultDialog.data?.error_output">
        <h4>错误输出</h4>
        <pre class="output-box">{{ resultDialog.data?.error_output }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, ArrowDown, Edit, CopyDocument, Delete } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

const loading = ref(false)
const scripts = ref([])
const formRef = ref(null)

const filters = reactive({
  script_type: '',
  search: ''
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false,
  id: null,
  form: {
    name: '',
    script_type: 'python',
    content: '',
    description: '',
    timeout: 300,
    max_retries: 0,
    is_public: false,
    tags: '',
    // 通知配置
    notify_on_success: false,
    notify_on_failure: true,
    notify_channels: []
  },
  rules: {
    name: [{ required: true, message: '请输入脚本名称', trigger: 'blur' }],
    script_type: [{ required: true, message: '请选择脚本类型', trigger: 'change' }],
    content: [{ required: true, message: '请输入脚本内容', trigger: 'blur' }]
  }
})

const execDialog = reactive({
  visible: false,
  scriptId: null,
  scriptName: '',
  params: '{}',
  async_exec: true,
  loading: false
})

const resultDialog = reactive({
  visible: false,
  data: null
})

const notificationChannels = ref([])

const fetchNotificationChannels = async () => {
  try {
    const data = await request.get('/notification/channels')
    notificationChannels.value = data
  } catch (error) {
    console.error('获取通知通道列表失败:', error)
  }
}

const fetchScripts = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.script_type) params.script_type = filters.script_type
    if (filters.search) params.search = filters.search
    
    const data = await request.get('/scripts', { params })
    scripts.value = data.items
    pagination.total = data.total
  } catch (error) {
    console.error('获取脚本列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  dialog.isEdit = false
  dialog.id = null
  dialog.form = {
    name: '',
    script_type: 'python',
    content: '',
    description: '',
    timeout: 300,
    max_retries: 0,
    is_public: false,
    tags: '',
    notify_on_success: false,
    notify_on_failure: true,
    notify_channels: []
  }
  dialog.visible = true
}

const handleEdit = async (row) => {
  try {
    const data = await request.get(`/scripts/${row.id}`)
    dialog.isEdit = true
    dialog.id = row.id
    dialog.form = {
      name: data.name,
      script_type: data.script_type,
      content: data.content,
      description: data.description || '',
      timeout: data.timeout,
      max_retries: data.max_retries,
      is_public: data.is_public,
      tags: data.tags || '',
      notify_on_success: data.notify_on_success || false,
      notify_on_failure: data.notify_on_failure ?? true,
      notify_channels: data.notify_channels ? data.notify_channels.split(',') : []
    }
    dialog.visible = true
  } catch (error) {
    ElMessage.error('获取脚本详情失败')
  }
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.submitting = true
    try {
      // 处理通知通道数据：将数组转为逗号分隔的字符串
      const submitData = {
        ...dialog.form,
        notify_channels: dialog.form.notify_channels.join(',')
      }
      
      if (dialog.isEdit) {
        await request.put(`/scripts/${dialog.id}`, submitData)
        ElMessage.success('更新成功')
      } else {
        await request.post('/scripts', submitData)
        ElMessage.success('创建成功')
      }
      dialog.visible = false
      fetchScripts()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      dialog.submitting = false
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此脚本吗？', '警告', { type: 'warning' })
    await request.delete(`/scripts/${row.id}`)
    ElMessage.success('删除成功')
    fetchScripts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleDuplicate = async (row) => {
  try {
    const result = await request.post(`/scripts/${row.id}/duplicate`)
    ElMessage.success(result.message)
    fetchScripts()
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleExecute = (row) => {
  execDialog.scriptId = row.id
  execDialog.scriptName = row.name
  execDialog.params = '{}'
  execDialog.async_exec = true
  execDialog.visible = true
}

const submitExecute = async () => {
  execDialog.loading = true
  try {
    let params = {}
    try {
      params = JSON.parse(execDialog.params)
    } catch (e) {
      params = {}
    }
    
    const result = await request.post(`/scripts/${execDialog.scriptId}/execute`, {
      params,
      async_exec: execDialog.async_exec
    })
    
    execDialog.visible = false
    
    if (execDialog.async_exec) {
      ElMessage.success(`脚本已提交执行，执行ID: ${result.execution_id}`)
    } else {
      // 同步执行，显示结果
      resultDialog.data = result
      resultDialog.visible = true
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '执行失败')
  } finally {
    execDialog.loading = false
  }
}

const getScriptTypeTag = (type) => {
  const tags = { python: 'success', bash: 'warning', sql: 'info' }
  return tags[type] || ''
}

const getStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', success: 'success', failed: 'danger', timeout: 'warning' }
  return types[status] || 'info'
}

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'

onMounted(() => {
  fetchScripts()
  fetchNotificationChannels()
})
</script>

<style lang="scss" scoped>
.scripts-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .search-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
  }
  
  .pagination {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
  }
  
  .code-editor {
    :deep(textarea) {
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 13px;
    }
  }
  
  .hint {
    margin-left: 10px;
    color: #909399;
    font-size: 12px;
  }
  
  .output-section {
    margin-top: 15px;
    
    h4 {
      margin-bottom: 8px;
      color: #606266;
    }
    
    .output-box {
      background: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      max-height: 300px;
      overflow: auto;
      white-space: pre-wrap;
    }
    
    &.error {
      .output-box {
        background: #fef0f0;
        color: #f56c6c;
      }
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
