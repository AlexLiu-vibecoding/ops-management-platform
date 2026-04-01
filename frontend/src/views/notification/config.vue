<template>
  <div class="notification-config-page">
    <!-- 静默规则管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">静默规则</span>
            <el-tag type="info" size="small">按时间或条件静默告警通知</el-tag>
          </div>
          <el-button type="primary" @click="handleAddSilenceRule" v-permission="'notification:silence_manage'">
            <el-icon><Plus /></el-icon>
            添加规则
          </el-button>
        </div>
      </template>
      
      <el-table :data="silenceRules" style="width: 100%" v-loading="silenceLoading">
        <el-table-column prop="name" label="规则名称" min-width="120" />
        <el-table-column prop="silence_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getSilenceTypeTag(row.silence_type)" size="small">
              {{ getSilenceTypeName(row.silence_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="生效时间" min-width="180">
          <template #default="{ row }">
            <template v-if="row.time_start && row.time_end">
              {{ row.time_start }} - {{ row.time_end }}
            </template>
            <template v-else-if="row.start_date && row.end_date">
              {{ formatDate(row.start_date) }} 至 {{ formatDate(row.end_date) }}
            </template>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="weekdays" label="生效星期" width="120">
          <template #default="{ row }">
            <span v-if="row.weekdays && row.weekdays.length > 0">
              {{ formatWeekdays(row.weekdays) }}
            </span>
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
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column label="操作" min-width="120" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="silenceActions" 
              @edit="handleEditSilenceRule"
              @delete="handleDeleteSilenceRule"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 频率限制规则管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">频率限制</span>
            <el-tag type="info" size="small">限制通知发送频率，避免通知轰炸</el-tag>
          </div>
          <el-button type="primary" @click="handleAddRateLimitRule" v-permission="'notification:rate_limit_manage'">
            <el-icon><Plus /></el-icon>
            添加规则
          </el-button>
        </div>
      </template>
      
      <el-table :data="rateLimitRules" style="width: 100%" v-loading="rateLimitLoading">
        <el-table-column prop="name" label="规则名称" min-width="120" />
        <el-table-column label="限制配置" min-width="200">
          <template #default="{ row }">
            <div class="rate-limit-info">
              <el-tag size="small" type="warning">
                {{ row.max_notifications }}次 / {{ row.limit_window }}秒
              </el-tag>
              <span class="text-gray-500 text-xs ml-2">冷却期: {{ row.cooldown_period }}秒</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="metric_type" label="指标类型" width="120">
          <template #default="{ row }">
            <span v-if="row.metric_type">{{ row.metric_type }}</span>
            <span v-else class="text-gray-400">全部</span>
          </template>
        </el-table-column>
        <el-table-column prop="alert_level" label="告警级别" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.alert_level" :type="getAlertLevelTag(row.alert_level)" size="small">
              {{ row.alert_level }}
            </el-tag>
            <span v-else class="text-gray-400">全部</span>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" align="center" />
        <el-table-column label="操作" min-width="120" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="rateLimitActions"
              @edit="handleEditRateLimitRule"
              @delete="handleDeleteRateLimitRule"
            />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 静默规则对话框 -->
    <el-dialog
      v-model="silenceDialog.visible"
      :title="silenceDialog.isEdit ? '编辑静默规则' : '添加静默规则'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="silenceDialog.form" :rules="silenceRules" ref="silenceFormRef" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="silenceDialog.form.name" placeholder="请输入规则名称" />
        </el-form-item>
        
        <el-form-item label="静默类型" prop="silence_type">
          <el-radio-group v-model="silenceDialog.form.silence_type">
            <el-radio label="once">一次性</el-radio>
            <el-radio label="daily">每日重复</el-radio>
            <el-radio label="weekly">每周重复</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="时间段" v-if="silenceDialog.form.silence_type !== 'once'">
          <el-col :span="11">
            <el-time-select
              v-model="silenceDialog.form.time_start"
              placeholder="开始时间"
              :max-time="silenceDialog.form.time_end"
            />
          </el-col>
          <el-col :span="2" class="text-center">-</el-col>
          <el-col :span="11">
            <el-time-select
              v-model="silenceDialog.form.time_end"
              placeholder="结束时间"
              :min-time="silenceDialog.form.time_start"
            />
          </el-col>
        </el-form-item>

        <el-form-item label="生效星期" v-if="silenceDialog.form.silence_type === 'weekly'">
          <el-checkbox-group v-model="silenceDialog.form.weekdays">
            <el-checkbox v-for="(day, index) in weekDays" :key="index" :label="index">
              {{ day }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="生效日期" v-if="silenceDialog.form.silence_type === 'once'">
          <el-date-picker
            v-model="silenceDialog.form.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
          />
        </el-form-item>

        <el-form-item label="匹配条件">
          <el-row :gutter="10">
            <el-col :span="12">
              <el-select v-model="silenceDialog.form.metric_type" placeholder="指标类型" clearable>
                <el-option label="CPU使用率" value="cpu_usage" />
                <el-option label="内存使用率" value="memory_usage" />
                <el-option label="磁盘使用率" value="disk_usage" />
                <el-option label="连接数" value="connections" />
                <el-option label="慢查询" value="slow_queries" />
              </el-select>
            </el-col>
            <el-col :span="12">
              <el-select v-model="silenceDialog.form.alert_level" placeholder="告警级别" clearable>
                <el-option label="严重" value="critical" />
                <el-option label="警告" value="warning" />
                <el-option label="信息" value="info" />
              </el-select>
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item label="优先级">
          <el-input-number v-model="silenceDialog.form.priority" :min="0" :max="100" />
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="silenceDialog.form.is_enabled" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="silenceDialog.form.description" type="textarea" :rows="2" placeholder="规则描述" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="silenceDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSilenceRule" :loading="silenceDialog.loading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 频率限制规则对话框 -->
    <el-dialog
      v-model="rateLimitDialog.visible"
      :title="rateLimitDialog.isEdit ? '编辑频率限制规则' : '添加频率限制规则'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="rateLimitDialog.form" :rules="rateLimitRules" ref="rateLimitFormRef" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="rateLimitDialog.form.name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="时间窗口(秒)" prop="limit_window">
          <el-input-number v-model="rateLimitDialog.form.limit_window" :min="60" :max="86400" />
        </el-form-item>

        <el-form-item label="最大通知数" prop="max_notifications">
          <el-input-number v-model="rateLimitDialog.form.max_notifications" :min="1" :max="100" />
        </el-form-item>

        <el-form-item label="冷却期(秒)" prop="cooldown_period">
          <el-input-number v-model="rateLimitDialog.form.cooldown_period" :min="60" :max="86400" />
        </el-form-item>

        <el-form-item label="匹配条件">
          <el-row :gutter="10">
            <el-col :span="12">
              <el-select v-model="rateLimitDialog.form.metric_type" placeholder="指标类型" clearable>
                <el-option label="CPU使用率" value="cpu_usage" />
                <el-option label="内存使用率" value="memory_usage" />
                <el-option label="磁盘使用率" value="disk_usage" />
                <el-option label="连接数" value="connections" />
                <el-option label="慢查询" value="slow_queries" />
              </el-select>
            </el-col>
            <el-col :span="12">
              <el-select v-model="rateLimitDialog.form.alert_level" placeholder="告警级别" clearable>
                <el-option label="严重" value="critical" />
                <el-option label="警告" value="warning" />
                <el-option label="信息" value="info" />
              </el-select>
            </el-col>
          </el-row>
        </el-form-item>

        <el-form-item label="优先级">
          <el-input-number v-model="rateLimitDialog.form.priority" :min="0" :max="100" />
        </el-form-item>

        <el-form-item label="是否启用">
          <el-switch v-model="rateLimitDialog.form.is_enabled" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="rateLimitDialog.form.description" type="textarea" :rows="2" placeholder="规则描述" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="rateLimitDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveRateLimitRule" :loading="rateLimitDialog.loading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/index'
import TableActions from '@/components/TableActions.vue'
import { formatDate as formatDateUtil } from '@/utils/format'

// 星期数组
const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 静默规则
const silenceRules = ref([])
const silenceLoading = ref(false)

// 频率限制规则
const rateLimitRules = ref([])
const rateLimitLoading = ref(false)

// 静默规则对话框
const silenceDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  currentId: null,
  form: {
    name: '',
    description: '',
    silence_type: 'once',
    time_start: '',
    time_end: '',
    weekdays: [],
    date_range: [],
    metric_type: '',
    alert_level: '',
    priority: 0,
    is_enabled: true
  }
})

// 频率限制对话框
const rateLimitDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  currentId: null,
  form: {
    name: '',
    description: '',
    limit_window: 300,
    max_notifications: 5,
    cooldown_period: 600,
    metric_type: '',
    alert_level: '',
    priority: 0,
    is_enabled: true
  }
})

// 表单引用
const silenceFormRef = ref(null)
const rateLimitFormRef = ref(null)

// 操作按钮
const silenceActions = [
  { key: 'edit', label: '编辑', permission: 'notification:silence_manage' },
  { key: 'delete', label: '删除', type: 'danger', permission: 'notification:silence_manage' }
]

const rateLimitActions = [
  { key: 'edit', label: '编辑', permission: 'notification:rate_limit_manage' },
  { key: 'delete', label: '删除', type: 'danger', permission: 'notification:rate_limit_manage' }
]

// 加载静默规则
const loadSilenceRules = async () => {
  silenceLoading.value = true
  try {
    const { data } = await request.get('/api/v1/notification/config/silence-rules')
    silenceRules.value = data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载静默规则失败')
  } finally {
    silenceLoading.value = false
  }
}

// 加载频率限制规则
const loadRateLimitRules = async () => {
  rateLimitLoading.value = true
  try {
    const { data } = await request.get('/api/v1/notification/config/rate-limit-rules')
    rateLimitRules.value = data
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载频率限制规则失败')
  } finally {
    rateLimitLoading.value = false
  }
}

// 添加静默规则
const handleAddSilenceRule = () => {
  silenceDialog.isEdit = false
  silenceDialog.currentId = null
  silenceDialog.form = {
    name: '',
    description: '',
    silence_type: 'once',
    time_start: '',
    time_end: '',
    weekdays: [],
    date_range: [],
    metric_type: '',
    alert_level: '',
    priority: 0,
    is_enabled: true
  }
  silenceDialog.visible = true
}

// 编辑静默规则
const handleEditSilenceRule = (row) => {
  silenceDialog.isEdit = true
  silenceDialog.currentId = row.id
  silenceDialog.form = {
    name: row.name,
    description: row.description || '',
    silence_type: row.silence_type,
    time_start: row.time_start || '',
    time_end: row.time_end || '',
    weekdays: row.weekdays || [],
    date_range: row.start_date && row.end_date ? [row.start_date, row.end_date] : [],
    metric_type: row.metric_type || '',
    alert_level: row.alert_level || '',
    priority: row.priority,
    is_enabled: row.is_enabled
  }
  silenceDialog.visible = true
}

// 保存静默规则
const handleSaveSilenceRule = async () => {
  await silenceFormRef.value.validate()
  
  silenceDialog.loading = true
  try {
    const payload = {
      name: silenceDialog.form.name,
      description: silenceDialog.form.description,
      silence_type: silenceDialog.form.silence_type,
      time_start: silenceDialog.form.time_start || null,
      time_end: silenceDialog.form.time_end || null,
      weekdays: silenceDialog.form.weekdays.length > 0 ? silenceDialog.form.weekdays : null,
      metric_type: silenceDialog.form.metric_type || null,
      alert_level: silenceDialog.form.alert_level || null,
      priority: silenceDialog.form.priority,
      is_enabled: silenceDialog.form.is_enabled
    }

    // 处理日期范围
    if (silenceDialog.form.date_range && silenceDialog.form.date_range.length === 2) {
      payload.start_date = silenceDialog.form.date_range[0]
      payload.end_date = silenceDialog.form.date_range[1]
    }

    if (silenceDialog.isEdit) {
      await request.put(`/api/v1/notification/config/silence-rules/${silenceDialog.currentId}`, payload)
      ElMessage.success('更新成功')
    } else {
      await request.post('/api/v1/notification/config/silence-rules', payload)
      ElMessage.success('创建成功')
    }

    silenceDialog.visible = false
    loadSilenceRules()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    silenceDialog.loading = false
  }
}

// 删除静默规则
const handleDeleteSilenceRule = async (row) => {
  await ElMessageBox.confirm('确定删除该静默规则吗？', '提示', {
    type: 'warning'
  })

  try {
    await request.delete(`/api/v1/notification/config/silence-rules/${row.id}`)
    ElMessage.success('删除成功')
    loadSilenceRules()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

// 添加频率限制规则
const handleAddRateLimitRule = () => {
  rateLimitDialog.isEdit = false
  rateLimitDialog.currentId = null
  rateLimitDialog.form = {
    name: '',
    description: '',
    limit_window: 300,
    max_notifications: 5,
    cooldown_period: 600,
    metric_type: '',
    alert_level: '',
    priority: 0,
    is_enabled: true
  }
  rateLimitDialog.visible = true
}

// 编辑频率限制规则
const handleEditRateLimitRule = (row) => {
  rateLimitDialog.isEdit = true
  rateLimitDialog.currentId = row.id
  rateLimitDialog.form = {
    name: row.name,
    description: row.description || '',
    limit_window: row.limit_window,
    max_notifications: row.max_notifications,
    cooldown_period: row.cooldown_period,
    metric_type: row.metric_type || '',
    alert_level: row.alert_level || '',
    priority: row.priority,
    is_enabled: row.is_enabled
  }
  rateLimitDialog.visible = true
}

// 保存频率限制规则
const handleSaveRateLimitRule = async () => {
  await rateLimitFormRef.value.validate()
  
  rateLimitDialog.loading = true
  try {
    const payload = {
      name: rateLimitDialog.form.name,
      description: rateLimitDialog.form.description,
      limit_window: rateLimitDialog.form.limit_window,
      max_notifications: rateLimitDialog.form.max_notifications,
      cooldown_period: rateLimitDialog.form.cooldown_period,
      metric_type: rateLimitDialog.form.metric_type || null,
      alert_level: rateLimitDialog.form.alert_level || null,
      priority: rateLimitDialog.form.priority,
      is_enabled: rateLimitDialog.form.is_enabled
    }

    if (rateLimitDialog.isEdit) {
      await request.put(`/api/v1/notification/config/rate-limit-rules/${rateLimitDialog.currentId}`, payload)
      ElMessage.success('更新成功')
    } else {
      await request.post('/api/v1/notification/config/rate-limit-rules', payload)
      ElMessage.success('创建成功')
    }

    rateLimitDialog.visible = false
    loadRateLimitRules()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    rateLimitDialog.loading = false
  }
}

// 删除频率限制规则
const handleDeleteRateLimitRule = async (row) => {
  await ElMessageBox.confirm('确定删除该频率限制规则吗？', '提示', {
    type: 'warning'
  })

  try {
    await request.delete(`/api/v1/notification/config/rate-limit-rules/${row.id}`)
    ElMessage.success('删除成功')
    loadRateLimitRules()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

// 辅助函数
const getSilenceTypeName = (type) => {
  const map = { once: '一次性', daily: '每日', weekly: '每周' }
  return map[type] || type
}

const getSilenceTypeTag = (type) => {
  const map = { once: '', daily: 'success', weekly: 'warning' }
  return map[type] || ''
}

const getAlertLevelTag = (level) => {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || ''
}

const formatWeekdays = (days) => {
  return days.map(d => weekDays[d]).join(', ')
}

const formatDate = (date) => {
  return formatDateUtil(date, 'YYYY-MM-DD')
}

onMounted(() => {
  loadSilenceRules()
  loadRateLimitRules()
})
</script>

<style scoped>
.notification-config-page {
  padding: 20px;
}

.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left .title {
  font-size: 16px;
  font-weight: 500;
}

.rate-limit-info {
  display: flex;
  align-items: center;
}

.dialog-form {
  max-height: 60vh;
  overflow-y: auto;
}

:deep(.el-checkbox-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
</style>
