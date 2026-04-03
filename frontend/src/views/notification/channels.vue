<template>
  <div class="notification-channels-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">通知管理</h2>
        <span class="page-desc">统一管理通知通道、静默规则和通知绑定</span>
      </div>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="channel-tabs" type="border-card">
      <!-- Tab 1: 通知通道 -->
      <el-tab-pane label="通知通道" name="channels">
        <template #label>
          <span class="tab-label">
            <el-icon><Message /></el-icon>
            <span>通知通道</span>
          </span>
        </template>
        
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <span class="title">通道列表</span>
                <el-tag type="info" size="small">钉钉、企微、飞书、邮件、Webhook</el-tag>
              </div>
              <el-button type="primary" @click="handleAddChannel" v-permission="'notification:channel_manage'">
                <el-icon><Plus /></el-icon>
                添加通道
              </el-button>
            </div>
          </template>
          
          <el-table :data="channels" style="width: 100%" v-loading="channelsLoading">
            <el-table-column prop="name" label="通道名称" min-width="150">
              <template #default="{ row }">
                <div class="channel-name">
                  <span>{{ row.name }}</span>
                  <el-tag v-if="!row.is_enabled" type="danger" size="small" class="ml-2">已禁用</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="channel_type_label" label="通道类型" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="getChannelTypeTag(row.channel_type)" size="small">
                  {{ row.channel_type_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="配置信息" min-width="200">
              <template #default="{ row }">
                <div class="config-info" v-if="row.config">
                  <span v-if="row.channel_type === 'dingtalk'" class="text-sm text-gray-500">
                    {{ maskWebhook(row.config.webhook) }}
                  </span>
                  <span v-else-if="row.channel_type === 'email'" class="text-sm text-gray-500">
                    {{ row.config.smtp_host }}:{{ row.config.smtp_port }}
                  </span>
                  <span v-else-if="row.channel_type === 'webhook'" class="text-sm text-gray-500">
                    {{ maskWebhook(row.config.url) }}
                  </span>
                  <span v-else class="text-sm text-gray-500">已配置</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="规则统计" width="120" align="center">
              <template #default="{ row }">
                <div class="rules-count">
                  <el-tag size="small">
                    静默: {{ row.silence_rules_count || 0 }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="is_enabled" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="180" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="handleTestChannel(row)">
                  测试
                </el-button>
                <el-button type="primary" link size="small" @click="handleEditChannel(row)">
                  编辑
                </el-button>
                <el-button type="danger" link size="small" @click="handleDeleteChannel(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Tab 2: 静默规则 -->
      <el-tab-pane label="静默规则" name="silence">
        <template #label>
          <span class="tab-label">
            <el-icon><Mute /></el-icon>
            <span>静默规则</span>
          </span>
        </template>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <span class="title">静默规则管理</span>
                <el-tag type="info" size="small">在特定条件下暂停发送通知</el-tag>
              </div>
              <div class="header-right">
                <el-select 
                  v-model="selectedChannelId" 
                  placeholder="请选择通道" 
                  clearable 
                  style="width: 200px; margin-right: 12px;"
                  @change="onChannelChange"
                >
                  <el-option 
                    v-for="channel in channels" 
                    :key="channel.id" 
                    :label="channel.name" 
                    :value="channel.id" 
                  />
                </el-select>
                <el-button 
                  type="primary" 
                  @click="handleAddSilenceRule" 
                  v-permission="'notification:silence_manage'"
                  :disabled="!selectedChannelId"
                >
                  <el-icon><Plus /></el-icon>
                  添加规则
                </el-button>
              </div>
            </div>
          </template>

          <el-alert 
            v-if="!selectedChannelId" 
            title="请先选择通知通道" 
            type="info" 
            :closable="false"
            class="mb-4"
          />
          
          <el-table :data="silenceRules" style="width: 100%" v-loading="silenceLoading" v-else>
            <el-table-column prop="name" label="规则名称" min-width="120" />
            <el-table-column prop="silence_type_label" label="类型" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="getSilenceTypeTag(row.silence_type)" size="small">
                  {{ row.silence_type_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel_name" label="所属通道" width="120">
              <template #default="{ row }">
                <span>{{ row.channel_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="生效时间" min-width="180">
              <template #default="{ row }">
                <template v-if="row.time_start && row.time_end">
                  {{ row.time_start }} - {{ row.time_end }}
                </template>
                <template v-else-if="row.start_time && row.end_time">
                  {{ formatDate(row.start_time) }} 至 {{ formatDate(row.end_time) }}
                </template>
                <span v-else class="text-gray-400">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="weekdays_label" label="生效星期" width="140">
              <template #default="{ row }">
                <span v-if="row.weekdays_label">{{ row.weekdays_label }}</span>
                <span v-else class="text-gray-400">-</span>
              </template>
            </el-table-column>
            <el-table-column label="匹配条件" min-width="150">
              <template #default="{ row }">
                <div class="match-conditions">
                  <el-tag v-if="row.instance_type" size="small" class="mr-1">
                    {{ row.instance_type }}
                  </el-tag>
                  <el-tag v-if="row.metric_type" size="small">
                    {{ row.metric_type }}
                  </el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="is_enabled" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'danger'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="120" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click="handleEditSilenceRule(row)">
                  编辑
                </el-button>
                <el-button type="danger" link size="small" @click="handleDeleteSilenceRule(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="selectedChannelId && silenceRules.length === 0 && !silenceLoading" description="暂无静默规则" />
        </el-card>
      </el-tab-pane>

      <!-- Tab 3: 通知绑定 -->
      <el-tab-pane label="通知绑定" name="bindings">
        <template #label>
          <span class="tab-label">
            <el-icon><Connection /></el-icon>
            <span>通知绑定</span>
          </span>
        </template>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <div class="header-left">
                <span class="title">通知绑定管理</span>
                <el-tag type="info" size="small">配置通知触发的范围和对象</el-tag>
              </div>
              <div class="header-right">
                <el-select 
                  v-model="selectedChannelId" 
                  placeholder="请选择通道" 
                  clearable 
                  style="width: 200px; margin-right: 12px;"
                  @change="onChannelChange"
                >
                  <el-option 
                    v-for="channel in channels" 
                    :key="channel.id" 
                    :label="channel.name" 
                    :value="channel.id" 
                  />
                </el-select>
                <el-button 
                  type="primary" 
                  @click="handleAddBinding" 
                  v-permission="'notification:channel_manage'"
                  :disabled="!selectedChannelId"
                >
                  <el-icon><Plus /></el-icon>
                  添加绑定
                </el-button>
              </div>
            </div>
          </template>

          <el-alert 
            v-if="!selectedChannelId" 
            title="请先选择通知通道" 
            type="info" 
            :closable="false"
            class="mb-4"
          />
          
          <el-table :data="bindings" style="width: 100%" v-loading="bindingsLoading" v-else>
            <el-table-column prop="notification_type" label="通知类型" min-width="120">
              <template #default="{ row }">
                <el-tag size="small">
                  {{ notificationTypes.find(t => t.value === row.notification_type)?.label || row.notification_type }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel_name" label="所属通道" width="120">
              <template #default="{ row }">
                <span>{{ row.channel_name || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="绑定范围" min-width="200">
              <template #default="{ row }">
                <div v-if="row.environment_name">
                  <el-tag size="small" type="info">环境: {{ row.environment_name }}</el-tag>
                </div>
                <div v-else-if="row.rdb_instance_name">
                  <el-tag size="small" type="warning">MySQL/PG: {{ row.rdb_instance_name }}</el-tag>
                </div>
                <div v-else-if="row.redis_instance_name">
                  <el-tag size="small" type="danger">Redis: {{ row.redis_instance_name }}</el-tag>
                </div>
                <div v-else-if="row.scheduled_task_name">
                  <el-tag size="small" type="success">任务: {{ row.scheduled_task_name }}</el-tag>
                </div>
                <span v-else class="text-gray-400">全局绑定</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right" align="center">
              <template #default="{ row }">
                <el-button type="danger" link size="small" @click="handleDeleteBinding(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-if="selectedChannelId && bindings.length === 0 && !bindingsLoading" description="暂无绑定" />
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 通道对话框 -->
    <el-dialog
      v-model="channelDialog.visible"
      :title="channelDialog.isEdit ? '编辑通道' : '添加通道'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="channelDialog.form" :rules="channelRules" ref="channelFormRef" label-width="100px">
        <el-form-item label="通道名称" prop="name">
          <el-input v-model="channelDialog.form.name" placeholder="请输入通道名称" />
        </el-form-item>

        <el-form-item label="通道类型" prop="channel_type">
          <el-select v-model="channelDialog.form.channel_type" placeholder="请选择通道类型" :disabled="channelDialog.isEdit" style="width: 100%">
            <el-option v-for="t in channelTypes" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </el-form-item>

        <!-- 钉钉配置 -->
        <template v-if="channelDialog.form.channel_type === 'dingtalk'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelDialog.form.config.webhook" placeholder="钉钉机器人Webhook地址" />
          </el-form-item>
          <el-form-item label="认证方式">
            <el-radio-group v-model="channelDialog.form.config.auth_type">
              <el-radio value="none">无认证</el-radio>
              <el-radio value="keyword">关键词</el-radio>
              <el-radio value="signature">加签</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="关键词" v-if="channelDialog.form.config.auth_type === 'keyword'">
            <el-select v-model="channelDialog.form.config.keywords" multiple placeholder="请输入关键词" 
                       allow-create filterable default-first-option />
          </el-form-item>
          <el-form-item label="Secret" v-if="channelDialog.form.config.auth_type === 'signature'">
            <el-input v-model="channelDialog.form.config.secret" placeholder="加签密钥" />
          </el-form-item>
        </template>

        <!-- 企业微信配置 -->
        <template v-if="channelDialog.form.channel_type === 'wechat'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelDialog.form.config.webhook" placeholder="企微机器人Webhook地址" />
          </el-form-item>
        </template>

        <!-- 飞书配置 -->
        <template v-if="channelDialog.form.channel_type === 'feishu'">
          <el-form-item label="Webhook" prop="config.webhook">
            <el-input v-model="channelDialog.form.config.webhook" placeholder="飞书机器人Webhook地址" />
          </el-form-item>
        </template>

        <!-- 邮件配置 -->
        <template v-if="channelDialog.form.channel_type === 'email'">
          <el-form-item label="SMTP服务器" prop="config.smtp_host">
            <el-input v-model="channelDialog.form.config.smtp_host" placeholder="smtp.example.com" />
          </el-form-item>
          <el-form-item label="端口" prop="config.smtp_port">
            <el-input-number v-model="channelDialog.form.config.smtp_port" :min="1" :max="65535" />
          </el-form-item>
          <el-form-item label="用户名" prop="config.username">
            <el-input v-model="channelDialog.form.config.username" placeholder="SMTP用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="config.password">
            <el-input v-model="channelDialog.form.config.password" type="password" placeholder="SMTP密码" />
          </el-form-item>
          <el-form-item label="发件人" prop="config.from_addr">
            <el-input v-model="channelDialog.form.config.from_addr" placeholder="发件人邮箱" />
          </el-form-item>
          <el-form-item label="使用TLS">
            <el-switch v-model="channelDialog.form.config.use_tls" />
          </el-form-item>
        </template>

        <!-- Webhook配置 -->
        <template v-if="channelDialog.form.channel_type === 'webhook'">
          <el-form-item label="URL" prop="config.url">
            <el-input v-model="channelDialog.form.config.url" placeholder="Webhook URL" />
          </el-form-item>
          <el-form-item label="请求方法">
            <el-radio-group v-model="channelDialog.form.config.method">
              <el-radio value="POST">POST</el-radio>
              <el-radio value="GET">GET</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>

        <el-form-item label="启用状态">
          <el-switch v-model="channelDialog.form.is_enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="channelDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveChannel" :loading="channelDialog.loading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 静默规则对话框 -->
    <el-dialog
      v-model="silenceDialog.visible"
      :title="silenceDialog.isEdit ? '编辑静默规则' : '添加静默规则'"
      width="600px"
      destroy-on-close
    >
      <el-form :model="silenceDialog.form" :rules="silenceFormRules" ref="silenceFormRef" label-width="100px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="silenceDialog.form.name" placeholder="请输入规则名称" />
        </el-form-item>

        <el-form-item label="静默类型" prop="silence_type">
          <el-radio-group v-model="silenceDialog.form.silence_type">
            <el-radio-button value="once">一次性</el-radio-button>
            <el-radio-button value="daily">每日</el-radio-button>
            <el-radio-button value="weekly">每周</el-radio-button>
            <el-radio-button value="period">时间段</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <!-- 时间范围选择 -->
        <template v-if="silenceDialog.form.silence_type === 'period'">
          <el-form-item label="日期范围">
            <el-date-picker
              v-model="silenceDialog.form.date_range"
              type="daterange"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              style="width: 100%"
            />
          </el-form-item>
        </template>

        <template v-if="silenceDialog.form.silence_type === 'daily' || silenceDialog.form.silence_type === 'weekly'">
          <el-form-item label="生效时间">
            <el-time-picker
              v-model="silenceDialog.form.time_start"
              placeholder="开始时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 48%"
            />
            <span class="mx-2">至</span>
            <el-time-picker
              v-model="silenceDialog.form.time_end"
              placeholder="结束时间"
              format="HH:mm"
              value-format="HH:mm"
              style="width: 48%"
            />
          </el-form-item>
        </template>

        <template v-if="silenceDialog.form.silence_type === 'weekly'">
          <el-form-item label="生效星期">
            <el-checkbox-group v-model="silenceDialog.form.weekdays">
              <el-checkbox v-for="(day, index) in weekDays" :key="index" :label="index + 1">{{ day }}</el-checkbox>
            </el-checkbox-group>
          </el-form-item>
        </template>

        <el-form-item label="实例类型">
          <el-select v-model="silenceDialog.form.instance_type" placeholder="全部类型" clearable style="width: 100%">
            <el-option label="MySQL/PG" value="rdb" />
            <el-option label="Redis" value="redis" />
          </el-select>
        </el-form-item>

        <el-form-item label="指标类型">
          <el-select v-model="silenceDialog.form.metric_type" placeholder="全部指标" clearable style="width: 100%">
            <el-option label="CPU" value="cpu" />
            <el-option label="内存" value="memory" />
            <el-option label="磁盘" value="disk" />
            <el-option label="连接数" value="connections" />
            <el-option label="QPS" value="qps" />
            <el-option label="慢查询" value="slow_query" />
          </el-select>
        </el-form-item>

        <el-form-item label="启用规则">
          <el-switch v-model="silenceDialog.form.is_enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="silenceDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveSilenceRule" :loading="silenceDialog.loading">保存</el-button>
      </template>
    </el-dialog>

    <!-- 绑定对话框 -->
    <el-dialog
      v-model="bindingDialog.visible"
      title="添加通知绑定"
      width="500px"
      destroy-on-close
    >
      <el-form :model="bindingForm" label-width="100px">
        <el-form-item label="通知类型" required>
          <el-select v-model="bindingForm.notification_type" placeholder="请选择通知类型" style="width: 100%">
            <el-option
              v-for="item in notificationTypes"
              :key="item.value"
              :label="item.label"
              :value="item.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="环境">
          <el-select v-model="bindingForm.environment_id" placeholder="选择环境（可选）" clearable style="width: 100%">
            <el-option v-for="env in environments" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="MySQL/PG实例">
          <el-select v-model="bindingForm.rdb_instance_id" placeholder="选择实例（可选）" clearable style="width: 100%">
            <el-option v-for="inst in rdbInstances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="Redis实例">
          <el-select v-model="bindingForm.redis_instance_id" placeholder="选择实例（可选）" clearable style="width: 100%">
            <el-option v-for="inst in redisInstances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="定时任务">
          <el-select v-model="bindingForm.scheduled_task_id" placeholder="选择任务（可选）" clearable style="width: 100%">
            <el-option v-for="task in scheduledTasks" :key="task.id" :label="task.name" :value="task.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="bindingDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitBinding" :loading="bindingDialog.submitting">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Message, Mute, Connection } from '@element-plus/icons-vue'
import { notificationApi } from '@/api/notification'
import { formatDate as formatDateUtil } from '@/utils/format'
import request from '@/api/index'

// 当前激活的 Tab
const activeTab = ref('channels')

// 选中的通道ID（用于静默规则、通知绑定 Tab）
const selectedChannelId = ref(null)

// 通道列表
const channels = ref([])
const channelsLoading = ref(false)
const channelTypes = ref([])

// 静默规则
const silenceRules = ref([])
const silenceLoading = ref(false)

// 绑定管理
const bindings = ref([])
const bindingsLoading = ref(false)

const bindingDialog = reactive({
  visible: false,
  submitting: false
})

const bindingForm = reactive({
  channel_id: null,
  notification_type: '',
  environment_id: null,
  rdb_instance_id: null,
  redis_instance_id: null,
  scheduled_task_id: null
})

const notificationTypes = [
  { value: 'approval', label: '审批通知' },
  { value: 'alert', label: '告警通知' },
  { value: 'scheduled_task', label: '定时任务通知' },
  { value: 'operation', label: '审计日志通知' }
]

// 绑定数据源
const environments = ref([])
const rdbInstances = ref([])
const redisInstances = ref([])
const scheduledTasks = ref([])

// 星期几
const weekDays = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 表单引用
const channelFormRef = ref(null)
const silenceFormRef = ref(null)

// 通道对话框
const channelDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  id: null,
  form: {
    name: '',
    channel_type: 'dingtalk',
    config: {
      webhook: '',
      auth_type: 'none',
      keywords: [],
      secret: '',
      smtp_host: '',
      smtp_port: 25,
      username: '',
      password: '',
      from_addr: '',
      use_tls: true,
      url: '',
      method: 'POST'
    },
    is_enabled: true,
    description: ''
  }
})

// 静默规则对话框
const silenceDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  id: null,
  form: {
    name: '',
    description: '',
    silence_type: 'once',
    time_start: '',
    time_end: '',
    weekdays: [],
    date_range: [],
    instance_type: '',
    metric_type: '',
    is_enabled: true
  }
})

// 表单验证规则
const channelRules = {
  name: [{ required: true, message: '请输入通道名称', trigger: 'blur' }],
  channel_type: [{ required: true, message: '请选择通道类型', trigger: 'change' }]
}

const silenceFormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  silence_type: [{ required: true, message: '请选择静默类型', trigger: 'change' }]
}

// 加载通道列表
const loadChannels = async () => {
  channelsLoading.value = true
  try {
    const res = await notificationApi.getChannels()
    channels.value = res.items || []
  } catch (error) {
    console.error('加载通道失败:', error)
    ElMessage.error('加载通道失败')
  } finally {
    channelsLoading.value = false
  }
}

// 加载通道类型
const loadChannelTypes = async () => {
  try {
    const res = await notificationApi.getChannelTypes()
    channelTypes.value = res.data || []
  } catch (error) {
    console.error('加载通道类型失败:', error)
  }
}

// 通道选择变化
const onChannelChange = (channelId) => {
  selectedChannelId.value = channelId
  if (channelId) {
    if (activeTab.value === 'silence') {
      loadSilenceRules(channelId)
    } else if (activeTab.value === 'bindings') {
      loadBindings(channelId)
    }
  } else {
    silenceRules.value = []
    bindings.value = []
  }
}

// 加载静默规则
const loadSilenceRules = async (channelId) => {
  if (!channelId) return
  silenceLoading.value = true
  try {
    const res = await notificationApi.getSilenceRules(channelId)
    silenceRules.value = res.items || []
  } catch (error) {
    console.error('加载静默规则失败:', error)
    ElMessage.error('加载静默规则失败')
  } finally {
    silenceLoading.value = false
  }
}

// 加载通道绑定
const loadBindings = async (channelId) => {
  if (!channelId) return
  bindingsLoading.value = true
  try {
    const res = await notificationApi.getChannelBindings(channelId)
    bindings.value = res.items || []
  } catch (error) {
    console.error('加载绑定失败:', error)
    if (error.response?.status !== 404) {
      ElMessage.error('加载绑定失败')
    }
    bindings.value = []
  } finally {
    bindingsLoading.value = false
  }
}

// 监听 Tab 变化
watch(activeTab, (newTab) => {
  if (selectedChannelId.value) {
    if (newTab === 'silence') {
      loadSilenceRules(selectedChannelId.value)
    } else if (newTab === 'bindings') {
      loadBindings(selectedChannelId.value)
    }
  }
})

// 加载绑定数据源
const loadBindingData = async () => {
  try {
    const [envRes, rdbRes, redisRes, taskRes] = await Promise.all([
      request.get('/environments'),
      request.get('/rdb-instances'),
      request.get('/redis-instances'),
      request.get('/scheduled-tasks')
    ])
    environments.value = envRes.items || []
    rdbInstances.value = rdbRes.items || []
    redisInstances.value = redisRes.items || []
    scheduledTasks.value = taskRes.items || []
  } catch (error) {
    console.error('加载绑定数据失败:', error)
  }
}

// 添加绑定
const handleAddBinding = () => {
  if (!selectedChannelId.value) {
    ElMessage.warning('请先选择通道')
    return
  }
  bindingForm.channel_id = selectedChannelId.value
  bindingForm.notification_type = ''
  bindingForm.environment_id = null
  bindingForm.rdb_instance_id = null
  bindingForm.redis_instance_id = null
  bindingForm.scheduled_task_id = null
  bindingDialog.visible = true
}

// 删除绑定
const handleDeleteBinding = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此绑定？', '确认删除', {
      type: 'warning'
    })
    await notificationApi.deleteChannelBinding(selectedChannelId.value, row.id)
    ElMessage.success('删除成功')
    loadBindings(selectedChannelId.value)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除绑定失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 提交绑定
const submitBinding = async () => {
  bindingDialog.submitting = true
  try {
    await notificationApi.createChannelBinding(selectedChannelId.value, bindingForm)
    ElMessage.success('添加成功')
    bindingDialog.visible = false
    loadBindings(selectedChannelId.value)
  } catch (error) {
    console.error('添加绑定失败:', error)
    ElMessage.error(error.response?.data?.detail || '添加失败')
  } finally {
    bindingDialog.submitting = false
  }
}

// 添加通道
const handleAddChannel = () => {
  channelDialog.isEdit = false
  channelDialog.form = {
    name: '',
    channel_type: 'dingtalk',
    config: {
      webhook: '',
      auth_type: 'none',
      keywords: [],
      secret: '',
      smtp_host: '',
      smtp_port: 25,
      username: '',
      password: '',
      from_addr: '',
      use_tls: true,
      url: '',
      method: 'POST'
    },
    is_enabled: true,
    description: ''
  }
  channelDialog.visible = true
}

// 编辑通道
const handleEditChannel = (row) => {
  channelDialog.isEdit = true
  channelDialog.form = {
    name: row.name,
    channel_type: row.channel_type,
    config: { ...row.config },
    is_enabled: row.is_enabled,
    description: row.description
  }
  channelDialog.id = row.id
  channelDialog.visible = true
}

// 保存通道
const handleSaveChannel = async () => {
  if (!channelFormRef.value) return
  await channelFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    channelDialog.loading = true
    try {
      if (channelDialog.isEdit) {
        await notificationApi.updateChannel(channelDialog.id, channelDialog.form)
        ElMessage.success('更新成功')
      } else {
        await notificationApi.createChannel(channelDialog.form)
        ElMessage.success('创建成功')
      }
      channelDialog.visible = false
      loadChannels()
    } catch (error) {
      console.error('保存通道失败:', error)
      ElMessage.error(error.response?.data?.detail || '保存失败')
    } finally {
      channelDialog.loading = false
    }
  })
}

// 删除通道
const handleDeleteChannel = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该通道吗？关联的静默规则也将被删除。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await notificationApi.deleteChannel(row.id)
    ElMessage.success('删除成功')
    if (selectedChannelId.value === row.id) {
      selectedChannelId.value = null
    }
    loadChannels()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除通道失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 测试通道
const handleTestChannel = async (row) => {
  try {
    await notificationApi.testChannel(row.id)
    ElMessage.success('测试通知已发送，请检查接收情况')
  } catch (error) {
    console.error('测试通道失败:', error)
    ElMessage.error(error.response?.data?.detail || '测试失败')
  }
}

// 添加静默规则
const handleAddSilenceRule = () => {
  if (!selectedChannelId.value) {
    ElMessage.warning('请先选择通道')
    return
  }
  silenceDialog.isEdit = false
  silenceDialog.id = null
  silenceDialog.form = {
    name: '',
    description: '',
    silence_type: 'once',
    time_start: '',
    time_end: '',
    weekdays: [],
    date_range: [],
    instance_type: '',
    metric_type: '',
    is_enabled: true
  }
  silenceDialog.visible = true
}

// 编辑静默规则
const handleEditSilenceRule = (row) => {
  silenceDialog.isEdit = true
  silenceDialog.id = row.id
  silenceDialog.form = {
    name: row.name,
    description: row.description || '',
    silence_type: row.silence_type,
    time_start: row.time_start || '',
    time_end: row.time_end || '',
    weekdays: row.weekdays || [],
    date_range: row.start_time && row.end_time ? [row.start_time, row.end_time] : [],
    instance_type: row.instance_type || '',
    metric_type: row.metric_type || '',
    is_enabled: row.is_enabled
  }
  silenceDialog.visible = true
}

// 保存静默规则
const handleSaveSilenceRule = async () => {
  if (!silenceFormRef.value) return
  await silenceFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    silenceDialog.loading = true
    try {
      const data = { ...silenceDialog.form }
      if (data.silence_type === 'period' && data.date_range && data.date_range.length === 2) {
        data.start_time = data.date_range[0]
        data.end_time = data.date_range[1]
      }
      
      if (silenceDialog.isEdit) {
        await notificationApi.updateSilenceRule(selectedChannelId.value, silenceDialog.id, data)
        ElMessage.success('更新成功')
      } else {
        await notificationApi.createSilenceRule(selectedChannelId.value, data)
        ElMessage.success('创建成功')
      }
      silenceDialog.visible = false
      loadSilenceRules(selectedChannelId.value)
    } catch (error) {
      console.error('保存静默规则失败:', error)
      ElMessage.error(error.response?.data?.detail || '保存失败')
    } finally {
      silenceDialog.loading = false
    }
  })
}

// 删除静默规则
const handleDeleteSilenceRule = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此静默规则？', '确认删除', {
      type: 'warning'
    })
    await notificationApi.deleteSilenceRule(selectedChannelId.value, row.id)
    ElMessage.success('删除成功')
    loadSilenceRules(selectedChannelId.value)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除静默规则失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
const maskWebhook = (url) => {
  if (!url) return '-'
  try {
    const urlObj = new URL(url)
    const path = urlObj.pathname
    return `${urlObj.protocol}//${urlObj.hostname}/****${path.slice(-8)}`
  } catch {
    return url.slice(0, 20) + '...'
  }
}

const getChannelTypeTag = (type) => {
  const map = {
    dingtalk: 'primary',
    wechat: 'success',
    feishu: 'warning',
    email: 'info',
    webhook: 'danger'
  }
  return map[type] || 'info'
}

const getSilenceTypeTag = (type) => {
  const map = {
    once: 'info',
    daily: 'warning',
    weekly: 'success',
    period: 'danger'
  }
  return map[type] || 'info'
}

const formatDate = (date) => {
  if (!date) return '-'
  return formatDateUtil(date)
}

const formatDateTime = (date) => {
  if (!date) return '-'
  return formatDateUtil(date, 'YYYY-MM-DD HH:mm:ss')
}

const formatDuration = (seconds) => {
  if (seconds < 60) return `${seconds}秒`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}小时`
  return `${Math.floor(seconds / 86400)}天`
}

// 初始化
onMounted(() => {
  loadChannels()
  loadChannelTypes()
  loadBindingData()
})
</script>

<style scoped lang="scss">
.notification-channels-page {
  padding: 20px;
  
  .page-header {
    margin-bottom: 20px;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;
      
      .page-title {
        margin: 0;
        font-size: 20px;
        font-weight: 600;
        color: #303133;
      }
      
      .page-desc {
        color: #909399;
        font-size: 14px;
      }
    }
  }
  
  .channel-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 0;
    }
    
    :deep(.el-tabs__content) {
      padding: 20px;
      background: #fff;
      border: 1px solid #dcdfe6;
      border-top: none;
    }
    
    .tab-label {
      display: flex;
      align-items: center;
      gap: 6px;
      
      .el-icon {
        font-size: 16px;
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 10px;
      
      .title {
        font-size: 16px;
        font-weight: 600;
      }
    }
    
    .header-right {
      display: flex;
      align-items: center;
    }
  }
  
  .channel-name {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .config-info {
    color: #606266;
    font-size: 13px;
  }
  
  .rules-count {
    display: flex;
    justify-content: center;
    gap: 4px;
  }
  
  .match-conditions {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .rate-config {
    color: #606266;
    font-size: 13px;
  }
  
  .truncate-text {
    display: inline-block;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  
  .form-hint {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }
  
  .mb-4 {
    margin-bottom: 16px;
  }
  
  .mx-2 {
    margin: 0 8px;
  }
  
  .ml-2 {
    margin-left: 8px;
  }
  
  .mr-1 {
    margin-right: 4px;
  }
  
  .mr-2 {
    margin-right: 8px;
  }
  
  .text-gray-400 {
    color: #c0c4cc;
  }
  
  .text-sm {
    font-size: 13px;
  }
}
</style>