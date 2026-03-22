<template>
  <div class="notification-page">
    <!-- 通知通道管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>通知通道</span>
          <el-button type="primary" @click="handleAddChannel">
            <el-icon><Plus /></el-icon>
            添加通道
          </el-button>
        </div>
      </template>
      
      <el-table :data="channels" style="width: 100%" v-loading="channelLoading">
        <el-table-column prop="name" label="通道名称" width="150" />
        <el-table-column prop="channel_type_label" label="类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.channel_type_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="auth_type" label="验证方式" width="100">
          <template #default="{ row }">
            <el-tag :type="getAuthTypeTag(row.auth_type)" size="small">
              {{ getAuthTypeName(row.auth_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="is_enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleTestChannel(row)">测试</el-button>
              <el-button link type="primary" size="small" @click="handleEditChannel(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteChannel(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 通知绑定管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>通知绑定</span>
          <el-button type="primary" @click="handleAddBinding">
            <el-icon><Plus /></el-icon>
            添加绑定
          </el-button>
        </div>
      </template>
      
      <el-table :data="bindings" style="width: 100%" v-loading="bindingLoading">
        <el-table-column prop="channel_name" label="通道" width="150" />
        <el-table-column prop="channel_type" label="通道类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">钉钉</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="notification_type_label" label="通知类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getNotificationTypeTag(row.notification_type)" size="small">
              {{ row.notification_type_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_task_id" label="定时任务" width="150">
          <template #default="{ row }">
            <span v-if="row.scheduled_task_id">{{ getScheduledTaskName(row.scheduled_task_id) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="danger" size="small" @click="handleDeleteBinding(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑通道对话框 -->
    <el-dialog
      v-model="channelDialog.visible"
      :title="channelDialog.isEdit ? '编辑通道' : '添加通道'"
      width="550px"
      destroy-on-close
    >
      <el-form :model="channelDialog.form" label-width="100px">
        <el-form-item label="通道名称" required>
          <el-input v-model="channelDialog.form.name" placeholder="请输入通道名称" />
        </el-form-item>
        
        <el-form-item label="Webhook" required>
          <el-input v-model="channelDialog.form.webhook" placeholder="请输入Webhook地址" />
        </el-form-item>
        
        <el-form-item label="验证方式">
          <el-select v-model="channelDialog.form.auth_type" placeholder="请选择验证方式" style="width: 100%">
            <el-option label="无验证" value="none" />
            <el-option label="关键词" value="keyword" />
            <el-option label="加签" value="sign" />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="channelDialog.form.auth_type === 'sign'" label="密钥" required>
          <el-input v-model="channelDialog.form.secret" placeholder="请输入加签密钥" />
        </el-form-item>
        
        <el-form-item v-if="channelDialog.form.auth_type === 'keyword'" label="关键词" required>
          <el-select
            v-model="channelDialog.form.keywords"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入关键词后回车"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="channelDialog.form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        
        <el-form-item v-if="channelDialog.isEdit" label="启用状态">
          <el-switch v-model="channelDialog.form.is_enabled" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="channelDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveChannel" :loading="channelDialog.saving">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 添加绑定对话框 -->
    <el-dialog
      v-model="bindingDialog.visible"
      title="添加通知绑定"
      width="500px"
      destroy-on-close
    >
      <el-form :model="bindingDialog.form" label-width="100px">
        <el-form-item label="通知通道" required>
          <el-select v-model="bindingDialog.form.channel_id" placeholder="请选择通知通道" style="width: 100%">
            <el-option
              v-for="c in channels.filter(ch => ch.is_enabled)"
              :key="c.id"
              :label="`${c.name} (${c.channel_type_label})`"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="通知类型" required>
          <el-select v-model="bindingDialog.form.notification_type" placeholder="请选择通知类型" style="width: 100%">
            <el-option
              v-for="item in notificationTypes"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item v-if="bindingDialog.form.notification_type === 'scheduled_task'" label="定时任务">
          <el-select v-model="bindingDialog.form.scheduled_task_id" placeholder="选择定时任务（可选，不选则通知所有任务）" clearable style="width: 100%">
            <el-option
              v-for="task in scheduledTasks"
              :key="task.id"
              :label="task.name"
              :value="task.id"
            />
          </el-select>
          <div class="form-tip">不选择特定任务时，所有定时任务执行都会发送通知</div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="bindingDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveBinding" :loading="bindingDialog.saving">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/index'

// 数据
const channels = ref([])
const bindings = ref([])
const notificationTypes = ref([])
const channelLoading = ref(false)
const bindingLoading = ref(false)

// 通道对话框
const channelDialog = reactive({
  visible: false,
  isEdit: false,
  saving: false,
  editId: null,
  form: {
    name: '',
    webhook: '',
    auth_type: 'none',
    secret: '',
    keywords: [],
    description: '',
    is_enabled: true
  }
})

// 绑定对话框
const bindingDialog = reactive({
  visible: false,
  saving: false,
  form: {
    channel_id: null,
    notification_type: '',
    scheduled_task_id: null
  }
})

// 获取定时任务列表
const scheduledTasks = ref([])

// 获取通道列表
const fetchChannels = async () => {
  channelLoading.value = true
  try {
    channels.value = await request.get('/notification/channels')
  } catch (error) {
    console.error('获取通道列表失败:', error)
  } finally {
    channelLoading.value = false
  }
}

// 获取绑定列表
const fetchBindings = async () => {
  bindingLoading.value = true
  try {
    bindings.value = await request.get('/notification/bindings')
  } catch (error) {
    console.error('获取绑定列表失败:', error)
  } finally {
    bindingLoading.value = false
  }
}

// 获取通知类型
const fetchNotificationTypes = async () => {
  try {
    notificationTypes.value = await request.get('/notification/notification-types')
  } catch (error) {
    console.error('获取通知类型失败:', error)
  }
}

// 获取定时任务列表
const fetchScheduledTasks = async () => {
  try {
    const res = await request.get('/scheduled-tasks', { params: { limit: 100 } })
    scheduledTasks.value = res.items || []
  } catch (error) {
    console.error('获取定时任务失败:', error)
  }
}

// 添加通道
const handleAddChannel = () => {
  channelDialog.isEdit = false
  channelDialog.editId = null
  channelDialog.form = {
    name: '',
    webhook: '',
    auth_type: 'none',
    secret: '',
    keywords: [],
    description: '',
    is_enabled: true
  }
  channelDialog.visible = true
}

// 编辑通道
const handleEditChannel = async (row) => {
  channelDialog.isEdit = true
  channelDialog.editId = row.id
  
  try {
    const detail = await request.get(`/notification/channels/${row.id}`)
    channelDialog.form = {
      name: detail.name,
      webhook: detail.webhook || '',
      auth_type: detail.auth_type,
      secret: '',
      keywords: detail.keywords || [],
      description: detail.description || '',
      is_enabled: detail.is_enabled
    }
    channelDialog.visible = true
  } catch (error) {
    ElMessage.error('获取通道详情失败')
  }
}

// 保存通道
const handleSaveChannel = async () => {
  if (!channelDialog.form.name) {
    ElMessage.warning('请输入通道名称')
    return
  }
  if (!channelDialog.form.webhook) {
    ElMessage.warning('请输入Webhook地址')
    return
  }
  
  channelDialog.saving = true
  try {
    if (channelDialog.isEdit) {
      await request.put(`/notification/channels/${channelDialog.editId}`, channelDialog.form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/notification/channels', channelDialog.form)
      ElMessage.success('创建成功')
    }
    channelDialog.visible = false
    fetchChannels()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    channelDialog.saving = false
  }
}

// 删除通道
const handleDeleteChannel = (row) => {
  ElMessageBox.confirm('确定要删除该通知通道吗？相关的通知绑定也会被删除。', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/notification/channels/${row.id}`)
      ElMessage.success('删除成功')
      fetchChannels()
      fetchBindings()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 测试通道
const handleTestChannel = async (row) => {
  try {
    await request.post(`/notification/channels/${row.id}/test`, null, {
      params: { test_message: '来自OpsCenter的测试消息' }
    })
    ElMessage.success('测试消息发送成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送失败')
  }
}

// 添加绑定
const handleAddBinding = () => {
  bindingDialog.form = {
    channel_id: null,
    notification_type: '',
    scheduled_task_id: null
  }
  bindingDialog.visible = true
}

// 保存绑定
const handleSaveBinding = async () => {
  if (!bindingDialog.form.channel_id) {
    ElMessage.warning('请选择通知通道')
    return
  }
  if (!bindingDialog.form.notification_type) {
    ElMessage.warning('请选择通知类型')
    return
  }
  
  bindingDialog.saving = true
  try {
    await request.post('/notification/bindings', bindingDialog.form)
    ElMessage.success('绑定创建成功')
    bindingDialog.visible = false
    fetchBindings()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    bindingDialog.saving = false
  }
}

// 删除绑定
const handleDeleteBinding = (row) => {
  ElMessageBox.confirm('确定要删除该通知绑定吗？', '提示', {
    type: 'warning'
  }).then(async () => {
    try {
      await request.delete(`/notification/bindings/${row.id}`)
      ElMessage.success('删除成功')
      fetchBindings()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// 辅助函数
const getAuthTypeName = (type) => {
  const map = { none: '无验证', keyword: '关键词', sign: '加签', token: 'Token' }
  return map[type] || type
}

const getAuthTypeTag = (type) => {
  const map = { none: 'info', keyword: 'warning', sign: 'success', token: 'primary' }
  return map[type] || 'info'
}

const getNotificationTypeTag = (type) => {
  const map = { approval: 'primary', alert: 'danger', scheduled_task: 'warning', operation: 'info' }
  return map[type] || 'info'
}

const getScheduledTaskName = (taskId) => {
  const task = scheduledTasks.value.find(t => t.id === taskId)
  return task ? task.name : `任务 #${taskId}`
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  fetchNotificationTypes()
  fetchChannels()
  fetchBindings()
  fetchScheduledTasks()
})
</script>

<style lang="scss" scoped>
.notification-page {
  .section-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
  
  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
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
