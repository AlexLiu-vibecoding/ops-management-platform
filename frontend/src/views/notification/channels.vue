<template>
  <div class="notification-channels-page">
    <!-- 通道管理 -->
    <el-card shadow="never" class="section-card">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span class="title">通知通道</span>
            <el-tag type="info" size="small">统一管理钉钉、企微、飞书等通道</el-tag>
          </div>
          <el-button type="primary" @click="handleAddChannel" v-permission="'notification:channel_manage'">
            <el-icon><Plus /></el-icon>
            添加通道
          </el-button>
        </div>
      </template>
      
      <el-table :data="channels" style="width: 100%" v-loading="channelsLoading"
                highlight-current-row @current-change="handleChannelSelect">
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
        <el-table-column label="规则统计" width="160" align="center">
          <template #default="{ row }">
            <div class="rules-count">
              <el-tag size="small" class="mr-2">
                静默: {{ row.silence_rules_count || 0 }}
              </el-tag>
              <el-tag size="small">
                频率: {{ row.rate_limits_count || 0 }}
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
        <el-table-column label="操作" min-width="150" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click.stop="handleTestChannel(row)">
              测试
            </el-button>
            <el-button type="primary" link size="small" @click.stop="handleEditChannel(row)">
              编辑
            </el-button>
            <el-button type="danger" link size="small" @click.stop="handleDeleteChannel(row)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 选中通道后的规则管理 -->
    <template v-if="selectedChannel">
      <!-- 静默规则管理 -->
      <el-card shadow="never" class="section-card mt-4">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="title">静默规则</span>
              <el-tag type="info" size="small">通道: {{ selectedChannel.name }}</el-tag>
            </div>
            <el-button type="primary" size="small" @click="handleAddSilenceRule" v-permission="'notification:silence_manage'">
              <el-icon><Plus /></el-icon>
              添加规则
            </el-button>
          </div>
        </template>
        
        <el-table :data="silenceRules" style="width: 100%" v-loading="silenceLoading">
          <el-table-column prop="name" label="规则名称" min-width="120" />
          <el-table-column prop="silence_type_label" label="类型" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="getSilenceTypeTag(row.silence_type)" size="small">
                {{ row.silence_type_label }}
              </el-tag>
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
                <el-tag v-if="row.alert_level" :type="getAlertLevelTag(row.alert_level)" size="small" class="mr-1">
                  {{ row.alert_level }}
                </el-tag>
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
          <el-table-column label="操作" min-width="100" fixed="right" align="center">
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
      </el-card>

      <!-- 频率限制规则管理 -->
      <el-card shadow="never" class="section-card mt-4">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="title">频率限制</span>
              <el-tag type="info" size="small">通道: {{ selectedChannel.name }}</el-tag>
            </div>
            <el-button type="primary" size="small" @click="handleAddRateLimitRule" v-permission="'notification:rate_limit_manage'">
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
          <el-table-column label="匹配条件" min-width="150">
            <template #default="{ row }">
              <div class="match-conditions">
                <el-tag v-if="row.alert_level" :type="getAlertLevelTag(row.alert_level)" size="small" class="mr-1">
                  {{ row.alert_level }}
                </el-tag>
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
          <el-table-column label="操作" min-width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" @click="handleEditRateLimitRule(row)">
                编辑
              </el-button>
              <el-button type="danger" link size="small" @click="handleDeleteRateLimitRule(row)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 通知绑定管理 -->
      <el-card shadow="never" class="section-card mt-4">
        <template #header>
          <div class="card-header">
            <div class="header-left">
              <span class="title">通知绑定</span>
              <el-tag type="info" size="small">通道: {{ selectedChannel.name }}</el-tag>
            </div>
            <el-button type="primary" size="small" @click="handleAddBinding">
              <el-icon><Plus /></el-icon>
              添加绑定
            </el-button>
          </div>
        </template>
        
        <el-table :data="bindings" style="width: 100%" v-loading="bindingsLoading">
          <el-table-column prop="notification_type" label="通知类型" min-width="120">
            <template #default="{ row }">
              <el-tag size="small">
                {{ notificationTypes.find(t => t.value === row.notification_type)?.label || row.notification_type }}
              </el-tag>
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
        
        <el-empty v-if="!bindingsLoading && bindings.length === 0" description="暂无绑定" />
      </el-card>
    </template>

    <div v-else class="no-channel-selected mt-4">
      <el-empty description="请选择一个通道查看和管理规则" />
    </div>

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
          <el-select v-model="channelDialog.form.channel_type" placeholder="请选择通道类型" :disabled="channelDialog.isEdit">
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
            <el-input v-model="channelDialog.form.config.username" placeholder="邮箱用户名" />
          </el-form-item>
          <el-form-item label="密码" prop="config.password">
            <el-input v-model="channelDialog.form.config.password" type="password" placeholder="邮箱密码" show-password />
          </el-form-item>
          <el-form-item label="发件人" prop="config.from_addr">
            <el-input v-model="channelDialog.form.config.from_addr" placeholder="发件人邮箱地址" />
          </el-form-item>
          <el-form-item label="使用TLS">
            <el-switch v-model="channelDialog.form.config.use_tls" />
          </el-form-item>
        </template>

        <!-- Webhook配置 -->
        <template v-if="channelDialog.form.channel_type === 'webhook'">
          <el-form-item label="URL" prop="config.url">
            <el-input v-model="channelDialog.form.config.url" placeholder="https://example.com/webhook" />
          </el-form-item>
          <el-form-item label="请求方法">
            <el-select v-model="channelDialog.form.config.method">
              <el-option label="POST" value="POST" />
              <el-option label="GET" value="GET" />
            </el-select>
          </el-form-item>
        </template>

        <el-form-item label="是否启用">
          <el-switch v-model="channelDialog.form.is_enabled" />
        </el-form-item>

        <el-form-item label="描述">
          <el-input v-model="channelDialog.form.description" type="textarea" :rows="2" placeholder="通道描述" />
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
            <el-radio value="once">一次性</el-radio>
            <el-radio value="daily">每日重复</el-radio>
            <el-radio value="weekly">每周重复</el-radio>
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
            <el-checkbox v-for="(day, index) in weekDays" :key="index" :value="index">
              {{ day }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="生效日期" v-if="silenceDialog.form.silence_type === 'once'">
          <el-date-picker
            v-model="silenceDialog.form.date_range"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
          />
        </el-form-item>

        <el-form-item label="匹配条件">
          <el-row :gutter="10">
            <el-col :span="12">
              <el-select v-model="silenceDialog.form.instance_type" placeholder="实例类型" clearable>
                <el-option label="RDB" value="rdb" />
                <el-option label="Redis" value="redis" />
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

        <el-form-item label="指标类型">
          <el-select v-model="silenceDialog.form.metric_type" placeholder="指标类型" clearable>
            <el-option label="CPU使用率" value="cpu_usage" />
            <el-option label="内存使用率" value="memory_usage" />
            <el-option label="磁盘使用率" value="disk_usage" />
            <el-option label="连接数" value="connections" />
            <el-option label="慢查询" value="slow_queries" />
          </el-select>
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
      <el-form :model="rateLimitDialog.form" :rules="rateLimitFormRules" ref="rateLimitFormRef" label-width="120px">
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
              <el-select v-model="rateLimitDialog.form.instance_type" placeholder="实例类型" clearable>
                <el-option label="RDB" value="rdb" />
                <el-option label="Redis" value="redis" />
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

        <el-form-item label="指标类型">
          <el-select v-model="rateLimitDialog.form.metric_type" placeholder="指标类型" clearable>
            <el-option label="CPU使用率" value="cpu_usage" />
            <el-option label="内存使用率" value="memory_usage" />
            <el-option label="磁盘使用率" value="disk_usage" />
            <el-option label="连接数" value="connections" />
            <el-option label="慢查询" value="slow_queries" />
          </el-select>
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
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { notificationApi } from '@/api/notification'
import { formatDate as formatDateUtil } from '@/utils/format'
import request from '@/api/index'

// 通道相关
const channels = ref([])
const channelsLoading = ref(false)
const selectedChannel = ref(null)
const channelTypes = ref([])

// 静默规则相关
const silenceRules = ref([])
const silenceLoading = ref(false)

// 频率限制相关
const rateLimitRules = ref([])
const rateLimitLoading = ref(false)

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
const rateLimitFormRef = ref(null)

// 通道对话框
const channelDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
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
    alert_level: '',
    metric_type: '',
    is_enabled: true
  }
})

// 频率限制对话框
const rateLimitDialog = reactive({
  visible: false,
  isEdit: false,
  loading: false,
  id: null,
  form: {
    name: '',
    description: '',
    limit_window: 300,
    max_notifications: 5,
    cooldown_period: 600,
    instance_type: '',
    alert_level: '',
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

const rateLimitFormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  limit_window: [{ required: true, message: '请输入时间窗口', trigger: 'blur' }],
  max_notifications: [{ required: true, message: '请输入最大通知数', trigger: 'blur' }],
  cooldown_period: [{ required: true, message: '请输入冷却期', trigger: 'blur' }]
}

// 加载通道列表
const loadChannels = async () => {
  channelsLoading.value = true
  try {
    const res = await notificationApi.getChannels()
    // API 返回 { items: [...], total: n }
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

// 选择通道
const handleChannelSelect = (row) => {
  selectedChannel.value = row
  if (row) {
    loadSilenceRules(row.id)
    loadRateLimits(row.id)
    loadBindings(row.id)
  }
}

// 加载静默规则
const loadSilenceRules = async (channelId) => {
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

// 加载频率限制
const loadRateLimits = async (channelId) => {
  rateLimitLoading.value = true
  try {
    const res = await notificationApi.getRateLimits(channelId)
    rateLimitRules.value = res.items || []
  } catch (error) {
    console.error('加载频率限制失败:', error)
    ElMessage.error('加载频率限制失败')
  } finally {
    rateLimitLoading.value = false
  }
}

// 加载通道绑定
const loadBindings = async (channelId) => {
  bindingsLoading.value = true
  try {
    const res = await notificationApi.getChannelBindings(channelId)
    bindings.value = res.items || []
  } catch (error) {
    console.error('加载绑定失败:', error)
    // 404 表示暂无绑定，显示空列表
    if (error.response?.status !== 404) {
      ElMessage.error('加载绑定失败')
    }
    bindings.value = []
  } finally {
    bindingsLoading.value = false
  }
}

// 添加绑定
const handleAddBinding = () => {
  bindingForm.channel_id = selectedChannel.value.id
  bindingForm.notification_type = ''
  bindingForm.environment_id = null
  bindingForm.rdb_instance_id = null
  bindingForm.redis_instance_id = null
  bindingForm.scheduled_task_id = null
  bindingDialog.visible = true
}

// 编辑绑定
const handleEditBinding = (row) => {
  bindingForm.channel_id = selectedChannel.value.id
  bindingForm.notification_type = row.notification_type
  bindingForm.environment_id = row.environment_id
  bindingForm.rdb_instance_id = row.rdb_instance_id
  bindingForm.redis_instance_id = row.redis_instance_id
  bindingForm.scheduled_task_id = row.scheduled_task_id
  bindingDialog.visible = true
}

// 删除绑定
const handleDeleteBinding = async (row) => {
  try {
    await ElMessageBox.confirm('确定删除此绑定？', '确认删除', {
      type: 'warning'
    })
    await notificationApi.deleteChannelBinding(selectedChannel.value.id, row.id)
    ElMessage.success('删除成功')
    loadBindings(selectedChannel.value.id)
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
    await notificationApi.createChannelBinding(selectedChannel.value.id, bindingForm)
    ElMessage.success('添加成功')
    bindingDialog.visible = false
    loadBindings(selectedChannel.value.id)
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
    await ElMessageBox.confirm('确定要删除该通道吗？关联的静默规则和频率限制也将被删除。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await notificationApi.deleteChannel(row.id)
    ElMessage.success('删除成功')
    if (selectedChannel.value?.id === row.id) {
      selectedChannel.value = null
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
  if (!selectedChannel.value) {
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
    alert_level: '',
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
    description: row.description,
    silence_type: row.silence_type,
    time_start: row.time_start || '',
    time_end: row.time_end || '',
    weekdays: row.weekdays || [],
    instance_type: row.instance_type || '',
    alert_level: row.alert_level || '',
    metric_type: row.metric_type || '',
    is_enabled: row.is_enabled
  }
  if (row.start_time && row.end_time) {
    silenceDialog.form.date_range = [row.start_time, row.end_time]
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
      
      // 处理日期范围
      if (data.silence_type === 'once' && data.date_range?.length === 2) {
        data.start_time = data.date_range[0]
        data.end_time = data.date_range[1]
      }
      delete data.date_range
      
      if (silenceDialog.isEdit) {
        await notificationApi.updateSilenceRule(selectedChannel.value.id, silenceDialog.id, data)
        ElMessage.success('更新成功')
      } else {
        await notificationApi.createSilenceRule(selectedChannel.value.id, data)
        ElMessage.success('创建成功')
      }
      silenceDialog.visible = false
      loadSilenceRules(selectedChannel.value.id)
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
    await ElMessageBox.confirm('确定要删除该静默规则吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await notificationApi.deleteSilenceRule(selectedChannel.value.id, row.id)
    ElMessage.success('删除成功')
    loadSilenceRules(selectedChannel.value.id)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除静默规则失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 添加频率限制规则
const handleAddRateLimitRule = () => {
  if (!selectedChannel.value) {
    ElMessage.warning('请先选择通道')
    return
  }
  rateLimitDialog.isEdit = false
  rateLimitDialog.id = null
  rateLimitDialog.form = {
    name: '',
    description: '',
    limit_window: 300,
    max_notifications: 5,
    cooldown_period: 600,
    instance_type: '',
    alert_level: '',
    metric_type: '',
    is_enabled: true
  }
  rateLimitDialog.visible = true
}

// 编辑频率限制规则
const handleEditRateLimitRule = (row) => {
  rateLimitDialog.isEdit = true
  rateLimitDialog.id = row.id
  rateLimitDialog.form = {
    name: row.name,
    description: row.description,
    limit_window: row.limit_window,
    max_notifications: row.max_notifications,
    cooldown_period: row.cooldown_period,
    instance_type: row.instance_type || '',
    alert_level: row.alert_level || '',
    metric_type: row.metric_type || '',
    is_enabled: row.is_enabled
  }
  rateLimitDialog.visible = true
}

// 保存频率限制规则
const handleSaveRateLimitRule = async () => {
  if (!rateLimitFormRef.value) return
  await rateLimitFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    rateLimitDialog.loading = true
    try {
      if (rateLimitDialog.isEdit) {
        await notificationApi.updateRateLimit(selectedChannel.value.id, rateLimitDialog.id, rateLimitDialog.form)
        ElMessage.success('更新成功')
      } else {
        await notificationApi.createRateLimit(selectedChannel.value.id, rateLimitDialog.form)
        ElMessage.success('创建成功')
      }
      rateLimitDialog.visible = false
      loadRateLimits(selectedChannel.value.id)
    } catch (error) {
      console.error('保存频率限制失败:', error)
      ElMessage.error(error.response?.data?.detail || '保存失败')
    } finally {
      rateLimitDialog.loading = false
    }
  })
}

// 删除频率限制规则
const handleDeleteRateLimitRule = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该频率限制规则吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await notificationApi.deleteRateLimit(selectedChannel.value.id, row.id)
    ElMessage.success('删除成功')
    loadRateLimits(selectedChannel.value.id)
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除频率限制失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 工具函数
const formatDate = (date) => formatDateUtil(date)

const formatDateTime = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const maskWebhook = (url) => {
  if (!url) return '-'
  try {
    const urlObj = new URL(url)
    return `${urlObj.protocol}//${urlObj.host}/***`
  } catch {
    return url.substring(0, 30) + '...'
  }
}

const getChannelTypeTag = (type) => {
  const map = {
    dingtalk: 'primary',
    wechat: 'success',
    feishu: 'warning',
    email: 'info',
    webhook: ''
  }
  return map[type] || ''
}

const getSilenceTypeTag = (type) => {
  const map = {
    once: 'warning',
    daily: 'success',
    weekly: 'primary'
  }
  return map[type] || ''
}

const getAlertLevelTag = (level) => {
  const map = {
    critical: 'danger',
    warning: 'warning',
    info: 'info'
  }
  return map[level] || ''
}

// 加载绑定数据源
const loadBindingDataSources = async () => {
  try {
    // 并行加载所有数据源
    const [envRes, rdbRes, redisRes, taskRes] = await Promise.all([
      request.get('/environments').catch(() => ({ items: [] })),
      request.get('/rdb-instances').catch(() => ({ items: [] })),
      request.get('/redis-instances').catch(() => ({ items: [] })),
      request.get('/scheduled-tasks').catch(() => ({ items: [] }))
    ])
    
    environments.value = envRes.items || envRes || []
    rdbInstances.value = rdbRes.items || rdbRes || []
    redisInstances.value = redisRes.items || redisRes || []
    scheduledTasks.value = taskRes.items || taskRes || []
  } catch (error) {
    console.error('加载数据源失败:', error)
  }
}

// 初始化
onMounted(() => {
  loadChannels()
  loadChannelTypes()
  loadBindingDataSources()
})
</script>

<style scoped>
.notification-channels-page {
  padding: 0;
}

.section-card {
  margin-bottom: 16px;
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

.channel-name {
  display: flex;
  align-items: center;
}

.rules-count {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.match-conditions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.no-channel-selected {
  padding: 40px 0;
}
</style>
