<template>
  <div class="notification-config-page">
    <!-- 通知通道 -->
    <el-card shadow="never" style="margin-bottom: 16px;">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">通知通道</span>
            <span class="header-desc">配置告警通知的发送渠道，支持钉钉、企业微信等</span>
          </div>
          <el-button type="primary" size="small" @click="handleAddChannel">
            <el-icon><Plus /></el-icon>
            添加通道
          </el-button>
        </div>
      </template>
      
      <el-table :data="channels" style="width: 100%" v-loading="channelLoading">
        <el-table-column prop="name" label="通道名称" min-width="120" />
        <el-table-column prop="channel_type_label" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.channel_type_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="auth_type" label="验证方式" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getAuthTypeTag(row.auth_type)" size="small">
              {{ getAuthTypeName(row.auth_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button link type="primary" size="small" @click="handleTestChannel(row)">测试</el-button>
              <el-button link type="primary" size="small" @click="handleEditChannel(row)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteChannel(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 通知绑定 -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="header-title">通知绑定</span>
            <span class="header-desc">将通知类型与通道关联，实现告警自动推送</span>
          </div>
          <el-button type="primary" size="small" @click="handleAddBinding">
            <el-icon><Plus /></el-icon>
            添加绑定
          </el-button>
        </div>
      </template>
      
      <el-table :data="bindings" style="width: 100%" v-loading="bindingLoading">
        <el-table-column prop="channel_name" label="通知通道" min-width="120" />
        <el-table-column prop="notification_type_label" label="通知类型" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="getNotificationTypeTag(row.notification_type)" size="small">
              {{ row.notification_type_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_task_name" label="关联任务" min-width="150">
          <template #default="{ row }">
            <span v-if="row.scheduled_task_name">{{ row.scheduled_task_name }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" @click="handleDeleteBinding(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 通道对话框 -->
    <el-dialog v-model="channelDialog.visible" :title="channelDialog.isEdit ? '编辑通道' : '添加通道'" width="500px" destroy-on-close>
      <el-form :model="channelDialog.form" label-width="100px">
        <el-form-item label="通道名称" required>
          <el-input v-model="channelDialog.form.name" placeholder="请输入通道名称，如：运维告警群" />
        </el-form-item>
        <el-form-item label="通道类型" required>
          <el-select v-model="channelDialog.form.channel_type" style="width: 100%">
            <el-option label="钉钉" value="dingtalk" />
            <el-option label="企业微信" value="wecom" />
            <el-option label="飞书" value="feishu" />
            <el-option label="自定义Webhook" value="custom" />
          </el-select>
        </el-form-item>
        <el-form-item label="Webhook" required>
          <el-input v-model="channelDialog.form.webhook" placeholder="请输入Webhook地址" />
        </el-form-item>
        <el-form-item label="验证方式">
          <el-select v-model="channelDialog.form.auth_type" style="width: 100%">
            <el-option label="无验证" value="none" />
            <el-option label="关键词" value="keyword" />
            <el-option label="加签" value="sign" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="channelDialog.form.auth_type === 'sign'" label="密钥" required>
          <el-input v-model="channelDialog.form.secret" placeholder="请输入加签密钥" />
        </el-form-item>
        <el-form-item v-if="channelDialog.form.auth_type === 'keyword'" label="关键词" required>
          <el-select v-model="channelDialog.form.keywords" multiple filterable allow-create default-first-option placeholder="输入关键词后回车" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="channelDialog.form.description" type="textarea" :rows="2" placeholder="可选，描述该通道的用途" />
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

    <!-- 绑定对话框 -->
    <el-dialog v-model="bindingDialog.visible" title="添加通知绑定" width="450px" destroy-on-close>
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
            <el-option v-for="item in notificationTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="bindingDialog.form.notification_type === 'scheduled_task'" label="定时任务">
          <el-select v-model="bindingDialog.form.scheduled_task_id" placeholder="选择定时任务（可选）" clearable style="width: 100%">
            <el-option v-for="task in scheduledTasks" :key="task.id" :label="task.name" :value="task.id" />
          </el-select>
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
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

// ==================== 通知管理 ====================
const channels = ref([])
const bindings = ref([])
const notificationTypes = ref([])
const scheduledTasks = ref([])
const channelLoading = ref(false)
const bindingLoading = ref(false)

const channelDialog = reactive({
  visible: false,
  isEdit: false,
  saving: false,
  editId: null,
  form: { 
    name: '', 
    webhook: '', 
    channel_type: 'dingtalk',
    auth_type: 'none', 
    secret: '', 
    keywords: [], 
    description: '', 
    is_enabled: true 
  }
})

const bindingDialog = reactive({
  visible: false,
  saving: false,
  form: { channel_id: null, notification_type: '', scheduled_task_id: null }
})

const fetchChannels = async () => {
  channelLoading.value = true
  try { channels.value = await request.get('/notification/channels') } 
  finally { channelLoading.value = false }
}

const fetchBindings = async () => {
  bindingLoading.value = true
  try { bindings.value = await request.get('/notification/bindings').then(res => res.items || res) } 
  finally { bindingLoading.value = false }
}

const fetchNotificationTypes = async () => {
  try { notificationTypes.value = await request.get('/notification/notification-types') } catch {}
}

const fetchScheduledTasks = async () => {
  try { 
    const res = await request.get('/scheduled-tasks', { params: { limit: 100 } })
    scheduledTasks.value = res.items || [] 
  } catch {}
}

const handleAddChannel = () => {
  channelDialog.isEdit = false
  channelDialog.editId = null
  channelDialog.form = { 
    name: '', 
    webhook: '', 
    channel_type: 'dingtalk',
    auth_type: 'none', 
    secret: '', 
    keywords: [], 
    description: '', 
    is_enabled: true 
  }
  channelDialog.visible = true
}

const handleEditChannel = async (row) => {
  channelDialog.isEdit = true
  channelDialog.editId = row.id
  try {
    const detail = await request.get(`/notification/channels/${row.id}`)
    channelDialog.form = { 
      name: detail.name, 
      webhook: detail.webhook || '', 
      channel_type: detail.channel_type || 'dingtalk',
      auth_type: detail.auth_type, 
      secret: '', 
      keywords: detail.keywords || [], 
      description: detail.description || '', 
      is_enabled: detail.is_enabled 
    }
    channelDialog.visible = true
  } catch { ElMessage.error('获取通道详情失败') }
}

const handleSaveChannel = async () => {
  if (!channelDialog.form.name || !channelDialog.form.webhook) {
    ElMessage.warning('请填写通道名称和Webhook')
    return
  }
  channelDialog.saving = true
  try {
    if (channelDialog.isEdit) {
      await request.put(`/notification/channels/${channelDialog.editId}`, channelDialog.form)
    } else {
      await request.post('/notification/channels', channelDialog.form)
    }
    ElMessage.success('保存成功')
    channelDialog.visible = false
    fetchChannels()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    channelDialog.saving = false
  }
}

const handleDeleteChannel = (row) => {
  ElMessageBox.confirm('确定要删除该通知通道吗？相关的通知绑定也会被删除。', '提示', { type: 'warning' })
    .then(async () => {
      await request.delete(`/notification/channels/${row.id}`)
      ElMessage.success('删除成功')
      fetchChannels()
      fetchBindings()
    }).catch(() => {})
}

const handleTestChannel = async (row) => {
  try {
    await request.post(`/notification/channels/${row.id}/test`, null, { params: { test_message: '来自OpsCenter的测试消息' } })
    ElMessage.success('测试消息发送成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '发送失败')
  }
}

const handleAddBinding = () => {
  bindingDialog.form = { channel_id: null, notification_type: '', scheduled_task_id: null }
  bindingDialog.visible = true
}

const handleSaveBinding = async () => {
  if (!bindingDialog.form.channel_id || !bindingDialog.form.notification_type) {
    ElMessage.warning('请选择通知通道和通知类型')
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

const handleDeleteBinding = (row) => {
  ElMessageBox.confirm('确定要删除该通知绑定吗？', '提示', { type: 'warning' })
    .then(async () => {
      await request.delete(`/notification/bindings/${row.id}`)
      ElMessage.success('删除成功')
      fetchBindings()
    }).catch(() => {})
}

const getAuthTypeName = (type) => ({ none: '无验证', keyword: '关键词', sign: '加签', token: 'Token' }[type] || type)
const getAuthTypeTag = (type) => ({ none: 'info', keyword: 'warning', sign: 'success', token: 'primary' }[type] || 'info')
const getNotificationTypeTag = (type) => ({ approval: 'primary', alert: 'danger', scheduled_task: 'warning', operation: 'info' }[type] || 'info')

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'

onMounted(() => {
  fetchNotificationTypes()
  fetchChannels()
  fetchBindings()
  fetchScheduledTasks()
})
</script>

<style lang="scss" scoped>
.notification-config-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      flex-direction: column;
      gap: 4px;
      
      .header-title {
        font-size: 15px;
        font-weight: 500;
        color: var(--el-text-color-primary);
      }
      
      .header-desc {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
  
  .action-buttons {
    display: flex;
    gap: 8px;
    justify-content: center;
    white-space: nowrap;
  }
  
  .text-muted {
    color: var(--el-text-color-placeholder);
  }
}
</style>
