<template>
  <div class="dingtalk-page">
    <!-- 钉钉通道管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>钉钉机器人通道</span>
          <el-button type="primary" @click="handleAddChannel">
            <el-icon><Plus /></el-icon>
            添加通道
          </el-button>
        </div>
      </template>
      
      <el-table :data="channels" style="width: 100%" v-loading="channelLoading">
        <el-table-column prop="name" label="通道名称" width="180" />
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column prop="is_enabled" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleTestChannel(row)">测试</el-button>
            <el-button text type="primary" @click="handleEditChannel(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDeleteChannel(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 通知绑定管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <span>通知绑定规则</span>
          <el-button type="primary" @click="handleAddBinding">
            <el-icon><Plus /></el-icon>
            添加绑定
          </el-button>
        </div>
      </template>
      
      <el-table :data="bindings" style="width: 100%" v-loading="bindingLoading">
        <el-table-column prop="channel_name" label="通道" width="150" />
        <el-table-column prop="notification_type" label="通知类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getNotificationTypeTag(row.notification_type)" size="small">
              {{ getNotificationTypeName(row.notification_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="environment_id" label="环境" width="120">
          <template #default="{ row }">
            <span v-if="row.environment_id">{{ getEnvName(row.environment_id) }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="instance_id" label="实例" width="150">
          <template #default="{ row }">
            <span v-if="row.instance_id">实例ID: {{ row.instance_id }}</span>
            <span v-else>全部实例</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button text type="danger" @click="handleDeleteBinding(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑通道对话框 -->
    <el-dialog
      v-model="channelDialog.visible"
      :title="channelDialog.isEdit ? '编辑通道' : '添加通道'"
      width="500px"
      @close="resetChannelForm"
    >
      <el-form
        ref="channelFormRef"
        :model="channelDialog.form"
        :rules="channelDialog.rules"
        label-width="80px"
      >
        <el-form-item label="名称" prop="name">
          <el-input v-model="channelDialog.form.name" placeholder="请输入通道名称" />
        </el-form-item>
        <el-form-item label="Webhook" prop="webhook">
          <el-input
            v-model="channelDialog.form.webhook"
            type="textarea"
            :rows="3"
            placeholder="请输入钉钉机器人Webhook地址"
          />
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="channelDialog.form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述"
          />
        </el-form-item>
        <el-form-item v-if="channelDialog.isEdit" label="状态">
          <el-switch v-model="channelDialog.form.is_enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="channelDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitChannel" :loading="channelDialog.loading">
          {{ channelDialog.isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 添加绑定对话框 -->
    <el-dialog
      v-model="bindingDialog.visible"
      title="添加通知绑定"
      width="500px"
      @close="resetBindingForm"
    >
      <el-form
        ref="bindingFormRef"
        :model="bindingDialog.form"
        :rules="bindingDialog.rules"
        label-width="80px"
      >
        <el-form-item label="通道" prop="channel_id">
          <el-select v-model="bindingDialog.form.channel_id" placeholder="请选择通道" style="width: 100%;">
            <el-option
              v-for="channel in channels"
              :key="channel.id"
              :label="channel.name"
              :value="channel.id"
              :disabled="!channel.is_enabled"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="通知类型" prop="notification_type">
          <el-select v-model="bindingDialog.form.notification_type" placeholder="请选择通知类型" style="width: 100%;">
            <el-option label="审批通知" value="approval" />
            <el-option label="告警通知" value="alert" />
            <el-option label="操作通知" value="operation" />
          </el-select>
        </el-form-item>
        <el-form-item label="环境">
          <el-select v-model="bindingDialog.form.environment_id" placeholder="全部环境" clearable style="width: 100%;">
            <el-option
              v-for="env in environments"
              :key="env.id"
              :label="env.name"
              :value="env.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="实例">
          <el-select v-model="bindingDialog.form.instance_id" placeholder="全部实例" clearable style="width: 100%;">
            <el-option
              v-for="instance in instances"
              :key="instance.id"
              :label="instance.name"
              :value="instance.id"
            />
          </el-select>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="bindingDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBinding" :loading="bindingDialog.loading">添加</el-button>
      </template>
    </el-dialog>
    
    <!-- 测试通道对话框 -->
    <el-dialog v-model="testDialog.visible" title="测试钉钉通道" width="400px">
      <el-form label-width="80px">
        <el-form-item label="通道">
          <el-input :value="testDialog.channelName" disabled />
        </el-form-item>
        <el-form-item label="测试消息">
          <el-input
            v-model="testDialog.message"
            type="textarea"
            :rows="3"
            placeholder="请输入测试消息内容"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="testDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="sendTestMessage" :loading="testDialog.loading">发送</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { dingtalkApi } from '@/api/dingtalk'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'

// 通道相关
const channelLoading = ref(false)
const channels = ref([])

// 绑定相关
const bindingLoading = ref(false)
const bindings = ref([])

// 环境和实例
const environments = ref([])
const instances = ref([])

// 通道对话框
const channelDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  form: {
    name: '',
    webhook: '',
    description: '',
    is_enabled: true
  },
  rules: {
    name: [{ required: true, message: '请输入通道名称', trigger: 'blur' }],
    webhook: [{ required: true, message: '请输入Webhook地址', trigger: 'blur' }]
  }
})

// 绑定对话框
const bindingDialog = reactive({
  visible: false,
  loading: false,
  form: {
    channel_id: null,
    notification_type: '',
    environment_id: null,
    instance_id: null
  },
  rules: {
    channel_id: [{ required: true, message: '请选择通道', trigger: 'change' }],
    notification_type: [{ required: true, message: '请选择通知类型', trigger: 'change' }]
  }
})

// 测试对话框
const testDialog = reactive({
  visible: false,
  loading: false,
  channelId: null,
  channelName: '',
  message: '这是一条来自MySQL管理平台的测试消息'
})

const channelFormRef = ref(null)
const bindingFormRef = ref(null)

// 获取环境列表
const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 1000 })
    instances.value = data
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 获取通道列表
const fetchChannels = async () => {
  channelLoading.value = true
  try {
    const data = await dingtalkApi.getChannels()
    channels.value = data
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
    const data = await dingtalkApi.getBindings()
    bindings.value = data
  } catch (error) {
    console.error('获取绑定列表失败:', error)
  } finally {
    bindingLoading.value = false
  }
}

// 添加通道
const handleAddChannel = () => {
  channelDialog.isEdit = false
  channelDialog.visible = true
}

// 编辑通道
const handleEditChannel = (row) => {
  channelDialog.isEdit = true
  channelDialog.visible = true
  channelDialog.form = {
    id: row.id,
    name: row.name,
    webhook: '', // 安全考虑，不回显webhook
    description: row.description,
    is_enabled: row.is_enabled
  }
}

// 删除通道
const handleDeleteChannel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通道吗？关联的通知绑定也会被删除。', '警告', {
      type: 'warning'
    })
    await dingtalkApi.deleteChannel(row.id)
    ElMessage.success('删除成功')
    fetchChannels()
    fetchBindings()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 测试通道
const handleTestChannel = (row) => {
  testDialog.channelId = row.id
  testDialog.channelName = row.name
  testDialog.message = '这是一条来自MySQL管理平台的测试消息'
  testDialog.visible = true
}

// 发送测试消息
const sendTestMessage = async () => {
  if (!testDialog.message.trim()) {
    ElMessage.warning('请输入测试消息内容')
    return
  }
  
  testDialog.loading = true
  try {
    await dingtalkApi.testChannel(testDialog.channelId, testDialog.message)
    ElMessage.success('测试消息发送成功')
    testDialog.visible = false
  } catch (error) {
    console.error('发送失败:', error)
  } finally {
    testDialog.loading = false
  }
}

// 提交通道
const submitChannel = async () => {
  if (!channelFormRef.value) return
  
  await channelFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    channelDialog.loading = true
    try {
      if (channelDialog.isEdit) {
        await dingtalkApi.updateChannel(channelDialog.form.id, channelDialog.form)
        ElMessage.success('更新成功')
      } else {
        await dingtalkApi.createChannel(channelDialog.form)
        ElMessage.success('添加成功')
      }
      
      channelDialog.visible = false
      fetchChannels()
    } catch (error) {
      console.error('操作失败:', error)
    } finally {
      channelDialog.loading = false
    }
  })
}

// 添加绑定
const handleAddBinding = () => {
  bindingDialog.visible = true
}

// 删除绑定
const handleDeleteBinding = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该绑定吗？', '警告', {
      type: 'warning'
    })
    await dingtalkApi.deleteBinding(row.id)
    ElMessage.success('删除成功')
    fetchBindings()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

// 提交绑定
const submitBinding = async () => {
  if (!bindingFormRef.value) return
  
  await bindingFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    bindingDialog.loading = true
    try {
      await dingtalkApi.createBinding(bindingDialog.form)
      ElMessage.success('添加成功')
      bindingDialog.visible = false
      fetchBindings()
    } catch (error) {
      console.error('添加失败:', error)
    } finally {
      bindingDialog.loading = false
    }
  })
}

// 重置通道表单
const resetChannelForm = () => {
  channelDialog.form = {
    name: '',
    webhook: '',
    description: '',
    is_enabled: true
  }
}

// 重置绑定表单
const resetBindingForm = () => {
  bindingDialog.form = {
    channel_id: null,
    notification_type: '',
    environment_id: null,
    instance_id: null
  }
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 获取环境名称
const getEnvName = (envId) => {
  const env = environments.value.find(e => e.id === envId)
  return env ? env.name : '-'
}

// 获取通知类型名称
const getNotificationTypeName = (type) => {
  const typeMap = {
    approval: '审批通知',
    alert: '告警通知',
    operation: '操作通知'
  }
  return typeMap[type] || type
}

// 获取通知类型标签
const getNotificationTypeTag = (type) => {
  const tagMap = {
    approval: 'warning',
    alert: 'danger',
    operation: 'primary'
  }
  return tagMap[type] || 'info'
}

onMounted(() => {
  fetchEnvironments()
  fetchInstances()
  fetchChannels()
  fetchBindings()
})
</script>

<style lang="scss" scoped>
.dingtalk-page {
  .section-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
