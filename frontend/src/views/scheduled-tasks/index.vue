<template>
  <div class="scheduled-tasks-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>定时任务</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新建任务
          </el-button>
        </div>
      </template>
      
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px;">
          <el-option label="启用" value="enabled" />
          <el-option label="禁用" value="disabled" />
        </el-select>
        <el-input v-model="filters.search" placeholder="搜索任务名称" clearable style="width: 200px;" @keyup.enter="fetchTasks" />
        <el-button type="primary" @click="fetchTasks">搜索</el-button>
      </div>
      
      <!-- 任务列表 -->
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column prop="name" label="任务名称" min-width="120" show-overflow-tooltip />
        <el-table-column prop="script_name" label="关联脚本" min-width="100" show-overflow-tooltip />
        <el-table-column prop="cron_expression" label="Cron表达式" width="130">
          <template #default="{ row }">
            <code style="font-size: 12px;">{{ row.cron_expression }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'" size="small">
              {{ row.status === 'enabled' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="next_run_time" label="下次执行" width="160">
          <template #default="{ row }">
            {{ formatTime(row.next_run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="执行统计" width="100" align="center">
          <template #default="{ row }">
            <span style="color: #67c23a;">{{ row.success_count }}</span> / 
            <span style="color: #f56c6c;">{{ row.fail_count }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_by" label="创建人" width="80" show-overflow-tooltip />
        <el-table-column label="操作" min-width="160" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="getTaskActions(row)"
              :max-primary="2"
              @trigger="handleTrigger"
              @pause="handlePause"
              @resume="handleResume"
              @edit="handleEdit"
              @history="handleHistory"
              @delete="handleDelete"
            />
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
          @size-change="fetchTasks"
          @current-change="fetchTasks"
        />
      </div>
    </el-card>
    
    <!-- 新建/编辑任务对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑任务' : '新建任务'" width="700px" :close-on-click-modal="false">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="120px">
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入任务名称" />
        </el-form-item>
        
        <el-form-item label="关联脚本" prop="script_id">
          <el-select v-model="dialog.form.script_id" placeholder="请选择脚本" style="width: 100%;" filterable>
            <el-option v-for="s in availableScripts" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="Cron表达式" prop="cron_expression">
          <el-input v-model="dialog.form.cron_expression" placeholder="如: 0 0 * * * (每天0点)" @change="validateCron" />
          <div class="cron-preview" v-if="cronPreview.valid">
            <span>下次执行时间：</span>
            <span v-for="(time, idx) in cronPreview.next_times" :key="idx" class="time-item">
              {{ time }}
            </span>
          </div>
          <div class="cron-error" v-if="cronPreview.error">
            {{ cronPreview.error }}
          </div>
        </el-form-item>
        
        <el-form-item label="执行参数">
          <el-input
            v-model="dialog.form.params_str"
            type="textarea"
            :rows="3"
            placeholder="JSON格式的参数"
          />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="时区">
              <el-select v-model="dialog.form.timezone" style="width: 100%;" placeholder="选择时区">
                <el-option-group label="服务器时区">
                  <el-option :label="`自动检测 (${serverTimezone})`" :value="serverTimezone" />
                </el-option-group>
                <el-option-group label="常用时区">
                  <el-option label="Asia/Shanghai (北京时间)" value="Asia/Shanghai" />
                  <el-option label="Asia/Hong_Kong (香港时间)" value="Asia/Hong_Kong" />
                  <el-option label="Asia/Tokyo (东京时间)" value="Asia/Tokyo" />
                  <el-option label="Asia/Singapore (新加坡时间)" value="Asia/Singapore" />
                  <el-option label="America/New_York (纽约时间)" value="America/New_York" />
                  <el-option label="America/Los_Angeles (洛杉矶时间)" value="America/Los_Angeles" />
                  <el-option label="Europe/London (伦敦时间)" value="Europe/London" />
                  <el-option label="UTC (协调世界时)" value="UTC" />
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="保留历史">
              <el-input-number v-model="dialog.form.max_history" :min="10" :max="1000" />
              <span style="margin-left: 5px;">条</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="失败时通知">
              <el-switch v-model="dialog.form.notify_on_fail" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="成功时通知">
              <el-switch v-model="dialog.form.notify_on_success" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">
          {{ dialog.isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 执行历史对话框 -->
    <el-dialog v-model="historyDialog.visible" title="执行历史" width="900px">
      <el-table :data="historyDialog.items" v-loading="historyDialog.loading">
        <el-table-column prop="script_name" label="脚本" width="150" />
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="start_time" label="开始时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.start_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration?.toFixed(2) || '-' }}秒
          </template>
        </el-table-column>
        <el-table-column prop="exit_code" label="退出码" width="80" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="viewExecutionDetail(row)">详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, VideoPause, RefreshRight, Edit, Timer, DeleteFilled } from '@element-plus/icons-vue'
import TableActions from '@/components/TableActions.vue'
import request from '@/api/index'
import dayjs from 'dayjs'

// 获取浏览器本地时区作为服务器时区的默认显示
const getBrowserTimezone = () => {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Shanghai'
  } catch {
    return 'Asia/Shanghai'
  }
}
const serverTimezone = ref(getBrowserTimezone())

// 定时任务操作配置
const getTaskActions = (row) => {
  const actions = []
  
  // 执行按钮（仅启用状态可用）
  actions.push({ 
    key: 'trigger', 
    label: '执行', 
    event: 'trigger', 
    primary: true,
    visible: row.status === 'enabled',
    icon: VideoPlay
  })
  
  // 暂停/恢复按钮
  if (row.status === 'enabled') {
    actions.push({ 
      key: 'pause', 
      label: '暂停', 
      event: 'pause', 
      icon: VideoPause
    })
  } else {
    actions.push({ 
      key: 'resume', 
      label: '恢复', 
      event: 'resume', 
      icon: RefreshRight
    })
  }
  
  // 编辑
  actions.push({ 
    key: 'edit', 
    label: '编辑', 
    event: 'edit', 
    icon: Edit
  })
  
  // 历史记录
  actions.push({ 
    key: 'history', 
    label: '历史', 
    event: 'history', 
    icon: Timer
  })
  
  // 删除
  actions.push({ 
    key: 'delete', 
    label: '删除', 
    event: 'delete', 
    danger: true,
    divided: true,
    icon: DeleteFilled
  })
  
  return actions
}

const loading = ref(false)
const tasks = ref([])
const availableScripts = ref([])
const formRef = ref(null)

const filters = reactive({
  status: '',
  search: ''
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const cronPreview = reactive({
  valid: false,
  next_times: [],
  error: ''
})

const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false,
  id: null,
  form: {
    name: '',
    script_id: null,
    cron_expression: '',
    params_str: '{}',
    timezone: 'Asia/Shanghai',
    max_history: 100,
    notify_on_fail: true,
    notify_on_success: false
  },
  rules: {
    name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
    script_id: [{ required: true, message: '请选择脚本', trigger: 'change' }],
    cron_expression: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
  }
})

const historyDialog = reactive({
  visible: false,
  taskId: null,
  loading: false,
  items: []
})

const fetchTasks = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.limit,
      limit: pagination.limit
    }
    if (filters.status) params.status = filters.status
    if (filters.search) params.search = filters.search
    
    const data = await request.get('/scheduled-tasks', { params })
    tasks.value = data.items
    pagination.total = data.total
  } catch (error) {
    console.error('获取任务列表失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchAvailableScripts = async () => {
  try {
    const data = await request.get('/scripts', { params: { limit: 100 } })
    availableScripts.value = data.items
  } catch (error) {
    console.error('获取脚本列表失败:', error)
  }
}

const validateCron = async () => {
  if (!dialog.form.cron_expression) return
  
  try {
    const result = await request.post('/scheduled-tasks/validate-cron', null, {
      params: { cron_expression: dialog.form.cron_expression }
    })
    
    cronPreview.valid = result.valid
    cronPreview.next_times = result.next_times || []
    cronPreview.error = result.error || ''
  } catch (error) {
    cronPreview.valid = false
    cronPreview.error = '验证失败'
  }
}

const handleAdd = () => {
  dialog.isEdit = false
  dialog.id = null
  dialog.form = {
    name: '',
    script_id: null,
    cron_expression: '',
    params_str: '{}',
    timezone: serverTimezone.value,
    max_history: 100,
    notify_on_fail: true,
    notify_on_success: false
  }
  cronPreview.valid = false
  cronPreview.next_times = []
  cronPreview.error = ''
  dialog.visible = true
}

const handleEdit = async (row) => {
  try {
    const data = await request.get(`/scheduled-tasks/${row.id}`)
    dialog.isEdit = true
    dialog.id = row.id
    dialog.form = {
      name: data.name,
      script_id: data.script_id,
      cron_expression: data.cron_expression,
      params_str: JSON.stringify(data.params || {}),
      timezone: data.timezone,
      max_history: data.max_history,
      notify_on_fail: data.notify_on_fail,
      notify_on_success: data.notify_on_success
    }
    validateCron()
    dialog.visible = true
  } catch (error) {
    ElMessage.error('获取任务详情失败')
  }
}

const handleSubmit = async () => {
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    let params = {}
    try {
      params = JSON.parse(dialog.form.params_str)
    } catch (e) {
      params = {}
    }
    
    const submitData = {
      name: dialog.form.name,
      script_id: dialog.form.script_id,
      cron_expression: dialog.form.cron_expression,
      params,
      timezone: dialog.form.timezone,
      max_history: dialog.form.max_history,
      notify_on_fail: dialog.form.notify_on_fail,
      notify_on_success: dialog.form.notify_on_success
    }
    
    dialog.submitting = true
    try {
      if (dialog.isEdit) {
        await request.put(`/scheduled-tasks/${dialog.id}`, submitData)
        ElMessage.success('更新成功')
      } else {
        await request.post('/scheduled-tasks', submitData)
        ElMessage.success('创建成功')
      }
      dialog.visible = false
      fetchTasks()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      dialog.submitting = false
    }
  })
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除此任务吗？', '警告', { type: 'warning' })
    await request.delete(`/scheduled-tasks/${row.id}`)
    ElMessage.success('删除成功')
    fetchTasks()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleTrigger = async (row) => {
  try {
    await request.post(`/scheduled-tasks/${row.id}/trigger`)
    ElMessage.success('任务已触发执行')
  } catch (error) {
    ElMessage.error('触发失败')
  }
}

const handlePause = async (row) => {
  try {
    await request.post(`/scheduled-tasks/${row.id}/pause`)
    ElMessage.success('任务已暂停')
    fetchTasks()
  } catch (error) {
    ElMessage.error('暂停失败')
  }
}

const handleResume = async (row) => {
  try {
    await request.post(`/scheduled-tasks/${row.id}/resume`)
    ElMessage.success('任务已恢复')
    fetchTasks()
  } catch (error) {
    ElMessage.error('恢复失败')
  }
}

const handleHistory = async (row) => {
  historyDialog.taskId = row.id
  historyDialog.visible = true
  historyDialog.loading = true
  
  try {
    const data = await request.get(`/scheduled-tasks/${row.id}/history`)
    historyDialog.items = data.items
  } catch (error) {
    ElMessage.error('获取历史记录失败')
  } finally {
    historyDialog.loading = false
  }
}

const viewExecutionDetail = (row) => {
  // 跳转到脚本执行详情
  console.log('查看执行详情:', row.id)
}

const getStatusType = (status) => {
  const types = { pending: 'info', running: 'primary', success: 'success', failed: 'danger', timeout: 'warning' }
  return types[status] || 'info'
}

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'

// 获取服务器时区
const fetchServerTimezone = async () => {
  try {
    const result = await request.get('/scheduled-tasks/server-info/timezone')
    serverTimezone.value = result.timezone
  } catch (error) {
    console.error('获取服务器时区失败:', error)
  }
}

onMounted(() => {
  fetchTasks()
  fetchAvailableScripts()
  fetchServerTimezone()
})
</script>

<style lang="scss" scoped>
.scheduled-tasks-page {
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
  
  .table-operations {
    display: flex;
    align-items: center;
    gap: 8px;
    
    .el-button + .el-button {
      margin-left: 0;
    }
  }
  
  code {
    background: #f5f7fa;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 12px;
  }
  
  .cron-preview {
    margin-top: 8px;
    font-size: 12px;
    color: #67c23a;
    
    .time-item {
      display: inline-block;
      margin-right: 10px;
      background: #f0f9eb;
      padding: 2px 6px;
      border-radius: 4px;
    }
  }
  
  .cron-error {
    margin-top: 8px;
    font-size: 12px;
    color: #f56c6c;
  }
}
</style>
