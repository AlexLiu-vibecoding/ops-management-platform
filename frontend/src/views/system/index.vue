<template>
  <div class="system-settings">
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 系统概览 -->
      <el-tab-pane label="系统概览" name="overview">
        <template #label>
          <span class="tab-label"><el-icon><DataAnalysis /></el-icon>系统概览</span>
        </template>
        <el-card shadow="never" class="overview-card">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="系统版本">
              <el-tag>{{ overview.version }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Python 版本">
              {{ overview.python_version }}
            </el-descriptions-item>
            <el-descriptions-item label="数据库类型">
              <el-tag type="success">{{ overview.database_type }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="存储类型">
              <el-tag type="warning">{{ overview.storage_type }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Redis">
              <el-tag :type="overview.redis_enabled ? 'success' : 'info'">
                {{ overview.redis_enabled ? '已启用' : '未启用' }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="调度器">
              <el-tag :type="overview.scheduler_running ? 'success' : 'danger'">
                {{ overview.scheduler_running ? '运行中' : '已停止' }}
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-tab-pane>

      <!-- 后台任务 -->
      <el-tab-pane label="后台任务" name="scheduler">
        <template #label>
          <span class="tab-label">
            <el-icon><Timer /></el-icon>
            后台任务
            <el-badge v-if="runningJobs > 0" :value="runningJobs" :max="99" class="tab-badge" type="success" />
          </span>
        </template>
        
        <!-- 调度器状态 -->
        <el-row :gutter="16" style="margin-bottom: 16px;">
          <el-col :span="8">
            <el-card shadow="hover" class="status-card">
              <div class="status-header">
                <el-icon class="status-icon" :class="{ running: schedulerOverview.approval_scheduler?.is_running }">
                  <Timer />
                </el-icon>
                <div class="status-info">
                  <div class="status-title">审批调度器</div>
                  <div class="status-badge">
                    <el-tag :type="schedulerOverview.approval_scheduler?.is_running ? 'success' : 'danger'" size="small">
                      {{ schedulerOverview.approval_scheduler?.is_running ? '运行中' : '已停止' }}
                    </el-tag>
                    <span class="job-count">{{ schedulerOverview.approval_scheduler?.job_count || 0 }} 个任务</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover" class="status-card">
              <div class="status-header">
                <el-icon class="status-icon" :class="{ running: schedulerOverview.task_scheduler?.is_running }">
                  <Setting />
                </el-icon>
                <div class="status-info">
                  <div class="status-title">任务调度器</div>
                  <div class="status-badge">
                    <el-tag :type="schedulerOverview.task_scheduler?.is_running ? 'success' : 'danger'" size="small">
                      {{ schedulerOverview.task_scheduler?.is_running ? '运行中' : '已停止' }}
                    </el-tag>
                    <span class="job-count">{{ schedulerOverview.task_scheduler?.job_count || 0 }} 个任务</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover" class="status-card summary-card">
              <div class="status-header">
                <el-icon class="status-icon running"><DataAnalysis /></el-icon>
                <div class="status-info">
                  <div class="status-title">任务统计</div>
                  <div class="summary-stats">
                    <div class="stat-item"><span class="stat-label">总数</span><span class="stat-value">{{ schedulerOverview.total_jobs || 0 }}</span></div>
                    <div class="stat-item"><span class="stat-label running">运行</span><span class="stat-value running">{{ schedulerOverview.running_jobs || 0 }}</span></div>
                    <div class="stat-item"><span class="stat-label paused">暂停</span><span class="stat-value paused">{{ schedulerOverview.paused_jobs || 0 }}</span></div>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>任务列表</span>
              <el-button type="primary" :icon="Refresh" @click="fetchSchedulerOverview">刷新状态</el-button>
            </div>
          </template>
          
          <el-table :data="schedulerJobs" v-loading="schedulerLoading" style="width: 100%" :show-overflow-tooltip="false">
            <el-table-column prop="id" label="任务ID" width="200">
              <template #default="{ row }"><code class="job-id">{{ row.id }}</code></template>
            </el-table-column>
            <el-table-column prop="name" label="任务名称" min-width="150">
              <template #default="{ row }">
                <div class="job-name">
                  <span>{{ row.name }}</span>
                  <span v-if="row.description" class="job-desc">{{ row.description }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="task_type" label="类型" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getTaskTypeStyle(row.task_type)" size="small">{{ getTaskTypeLabel(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="trigger_type" label="触发方式" width="100">
              <template #default="{ row }">
                <div class="trigger-info">
                  <el-tag size="small" effect="plain">{{ getTriggerTypeLabel(row.trigger_type) }}</el-tag>
                  <span class="trigger-config">{{ row.trigger_config }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="next_run_time" label="下次执行" width="160">
              <template #default="{ row }">
                <span v-if="row.next_run_time">{{ formatTime(row.next_run_time) }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'running' ? 'success' : row.status === 'paused' ? 'warning' : 'info'" size="small">
                  {{ row.status === 'running' ? '运行中' : row.status === 'paused' ? '已暂停' : '待执行' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right" align="center">
              <template #default="{ row }">
                <el-button v-if="row.status === 'running'" link type="warning" size="small" @click="handleJobAction(row, 'pause')" :loading="row._actionLoading">暂停</el-button>
                <el-button v-if="row.status === 'paused'" link type="success" size="small" @click="handleJobAction(row, 'resume')" :loading="row._actionLoading">恢复</el-button>
                <el-button link type="primary" size="small" @click="handleJobAction(row, 'trigger')" :loading="row._actionLoading">立即执行</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 数据库类型配置 -->
      <el-tab-pane label="数据库类型" name="database">
        <template #label>
          <span class="tab-label"><el-icon><Coin /></el-icon>数据库类型</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>支持的数据库类型</span>
              <el-tag type="info" size="small">配置后需要刷新页面生效</el-tag>
            </div>
          </template>
          
          <el-table :data="databaseConfigs" style="width: 100%">
            <el-table-column label="数据库" width="200">
              <template #default="{ row }">
                <div class="db-type-cell">
                  <el-icon :size="24" :color="getDbColor(row.db_type)">
                    <component :is="getDbIcon(row.db_type)" />
                  </el-icon>
                  <div class="db-info">
                    <div class="db-name">{{ row.display_name }}</div>
                    <div class="db-desc">{{ row.description }}</div>
                  </div>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="默认端口" width="120">
              <template #default="{ row }"><el-tag type="info">{{ row.default_port }}</el-tag></template>
            </el-table-column>
            <el-table-column label="状态" min-width="120">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" :loading="row.saving" @change="handleDbConfigChange(row)" />
              </template>
            </el-table-column>
            <el-table-column label="说明">
              <template #default="{ row }">
                <span v-if="row.enabled" class="hint success">用户在添加实例时可以选择此数据库类型</span>
                <span v-else class="hint warning">已禁用，用户无法添加此类型的实例</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- AWS 配置 -->
      <el-tab-pane label="AWS配置" name="aws">
        <template #label>
          <span class="tab-label"><el-icon><Cloudy /></el-icon>AWS配置</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>AWS 凭证配置</span>
              <el-tag type="warning" size="small">用于 RDS CloudWatch 指标采集</el-tag>
            </div>
          </template>

          <el-alert title="配置说明" type="info" :closable="false" show-icon style="margin-bottom: 20px;">
            <template #default>
              <p>配置 AWS 凭证后，系统可以自动采集 RDS 实例的 CloudWatch 性能指标。</p>
              <p style="margin-top: 8px;">凭证配置优先级：<strong>数据库配置 > 环境变量</strong></p>
            </template>
          </el-alert>

          <el-form :model="awsConfig" label-width="140px">
            <el-form-item label="AWS 区域">
              <el-select v-model="awsConfig.aws_region" placeholder="选择 AWS 区域" style="width: 100%;" :loading="awsRegionsLoading">
                <el-option-group v-for="group in awsRegionGroups" :key="group.geo_group" :label="group.geo_group">
                  <el-option v-for="region in group.regions" :key="region.region_code" :label="region.region_name" :value="region.region_code" />
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-divider content-position="left">AWS 凭证</el-divider>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="Access Key ID">
                  <el-input v-model="awsConfig.aws_access_key_id" placeholder="AKIAIOSFODNN7EXAMPLE" show-password />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Secret Access Key">
                  <el-input v-model="awsConfig.aws_secret_access_key" placeholder="wJalrXUtnFEMI..." show-password />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item>
              <el-button type="primary" @click="saveAwsConfig" :loading="savingAws">保存配置</el-button>
              <el-button @click="testAwsConfig" :loading="testingAws">测试连接</el-button>
              <el-button @click="resetAwsConfig">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 存储配置 -->
      <el-tab-pane label="存储配置" name="storage">
        <template #label>
          <span class="tab-label"><el-icon><Folder /></el-icon>存储配置</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>大文件存储配置</span>
              <el-tag type="warning" size="small">修改后需重启服务生效</el-tag>
            </div>
          </template>

          <el-form :model="storageConfig" label-width="140px">
            <el-form-item label="存储类型">
              <el-radio-group v-model="storageConfig.storage_type">
                <el-radio value="local"><el-icon><Folder /></el-icon>本地存储</el-radio>
                <el-radio value="s3"><el-icon><Cloudy /></el-icon>AWS S3</el-radio>
                <el-radio value="oss"><el-icon><Files /></el-icon>阿里云 OSS</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="文件保留天数">
                  <el-input-number v-model="storageConfig.retention_days" :min="1" :max="365" />
                  <span class="unit">天</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="大文件阈值">
                  <el-input-number v-model="storageConfig.size_threshold" :min="1000" :max="50000000" :step="100000" />
                  <span class="unit">字符</span>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 本地存储 -->
            <template v-if="storageConfig.storage_type === 'local'">
              <el-divider content-position="left">本地存储配置</el-divider>
              <el-form-item label="存储路径">
                <el-input v-model="storageConfig.local_path" placeholder="/app/data/sql_files" />
              </el-form-item>
            </template>

            <!-- AWS S3 -->
            <template v-if="storageConfig.storage_type === 's3'">
              <el-divider content-position="left">AWS S3 配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Bucket 名称"><el-input v-model="storageConfig.s3_bucket" placeholder="my-sql-files" /></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="区域"><el-input v-model="storageConfig.s3_region" placeholder="us-east-1" /></el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="端点URL">
                <el-input v-model="storageConfig.s3_endpoint" placeholder="可选，用于兼容 S3 的其他服务" />
              </el-form-item>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Access Key ID"><el-input v-model="storageConfig.s3_access_key_id" show-password /></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Secret Key"><el-input v-model="storageConfig.s3_secret_access_key" show-password /></el-form-item>
                </el-col>
              </el-row>
            </template>

            <!-- 阿里云 OSS -->
            <template v-if="storageConfig.storage_type === 'oss'">
              <el-divider content-position="left">阿里云 OSS 配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Bucket 名称"><el-input v-model="storageConfig.oss_bucket" /></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Endpoint"><el-input v-model="storageConfig.oss_endpoint" placeholder="oss-cn-hangzhou.aliyuncs.com" /></el-form-item>
                </el-col>
              </el-row>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Access Key ID"><el-input v-model="storageConfig.oss_access_key_id" show-password /></el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Access Key Secret"><el-input v-model="storageConfig.oss_access_key_secret" show-password /></el-form-item>
                </el-col>
              </el-row>
            </template>

            <el-form-item>
              <el-button type="primary" @click="saveStorageConfig" :loading="saving">保存配置</el-button>
              <el-button @click="testStorageConfig" :loading="testing">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 安全配置 -->
      <el-tab-pane label="安全配置" name="security">
        <template #label>
          <span class="tab-label"><el-icon><Lock /></el-icon>安全配置</span>
        </template>
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>安全配置</span>
              <el-tag type="danger" size="small">敏感信息，请妥善保管</el-tag>
            </div>
          </template>

          <el-alert title="安全提示" type="warning" :closable="false" show-icon style="margin-bottom: 20px;">
            以下密钥用于系统安全加密，请勿泄露。如需修改，请在服务器环境变量中配置。
          </el-alert>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="JWT 密钥">
              <div class="secret-value">
                <code>{{ securityConfig.jwt_secret_key }}</code>
                <el-tag v-if="jwtRotationData.current_version" type="success" size="small" style="margin-left: 10px;">
                  {{ jwtRotationData.current_version.toUpperCase() }}
                </el-tag>
                <el-tag :type="securityConfig.jwt_configured ? 'success' : 'warning'" size="small" style="margin-left: 5px;">
                  {{ securityConfig.jwt_configured ? '已自定义' : '使用默认值' }}
                </el-tag>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="AES 密钥">
              <div class="secret-value">
                <code>{{ securityConfig.aes_key }}</code>
                <el-tag v-if="overviewData.current_version" type="success" size="small" style="margin-left: 10px;">
                  {{ overviewData.current_version.toUpperCase() }}
                </el-tag>
                <el-tag :type="securityConfig.aes_configured ? 'success' : 'warning'" size="small" style="margin-left: 5px;">
                  {{ securityConfig.aes_configured ? '已自定义' : '使用默认值' }}
                </el-tag>
              </div>
            </el-descriptions-item>
            <el-descriptions-item label="Token 有效期">
              <el-tag type="primary">{{ securityConfig.token_expire_hours }} 小时</el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <!-- 密钥轮换区块 -->
          <el-divider content-position="left">
            <el-icon><Key /></el-icon> AES 密钥轮换
          </el-divider>
          
          <div class="key-rotation-section" v-loading="rotationLoading">
            <!-- AES 版本密钥列表 -->
            <el-card shadow="never" style="margin-bottom: 20px;">
              <template #header>
                <div class="card-header">
                  <span>AES 密钥版本</span>
                  <el-button type="primary" size="small" @click="handleGenerateKey" :loading="generatingKey">
                    <el-icon><Plus /></el-icon> 生成新版本
                  </el-button>
                </div>
              </template>
              <el-table :data="displayKeyVersions" size="small" border>
                <el-table-column prop="key_id" label="版本" width="100" align="center">
                  <template #default="{ row }">
                    <div class="version-cell">
                      <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
                        {{ row.key_id.toUpperCase() }}
                      </el-tag>
                      <el-tag v-if="row.is_active" type="success" size="small" style="margin-left: 4px; white-space: nowrap;">使用中</el-tag>
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="key_value_preview" label="密钥预览" min-width="150">
                  <template #default="{ row }">
                    <code>{{ row.key_value_preview }}</code>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="160">
                  <template #default="{ row }">
                    {{ formatTime(row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="180" align="center">
                  <template #default="{ row }">
                    <el-button 
                      v-if="!row.is_active" 
                      type="success" 
                      size="small" 
                      @click="handleSwitchVersion(row.key_id)"
                      :loading="switching">
                      切换
                    </el-button>
                    <el-button 
                      v-if="!row.is_active" 
                      type="danger" 
                      size="small" 
                      @click="handleDeleteKey(row.key_id)"
                      :loading="deletingKey === row.key_id">
                      删除
                    </el-button>
                    <span v-else class="text-muted">当前版本</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <!-- 统计信息 -->
            <el-row :gutter="20" class="rotation-stats">
              <el-col :span="12">
                <div class="rotation-stat-card">
                  <div class="stat-icon current"><el-icon><Key /></el-icon></div>
                  <div class="stat-info">
                    <div class="stat-label">当前版本</div>
                    <div class="stat-value">{{ overviewData.current_version?.toUpperCase() || '-' }}</div>
                  </div>
                </div>
              </el-col>
              <el-col :span="12">
                <div class="rotation-stat-card">
                  <div class="stat-icon total"><el-icon><Document /></el-icon></div>
                  <div class="stat-info">
                    <div class="stat-label">版本总数</div>
                    <div class="stat-value">{{ overviewData.total_keys || 0 }}</div>
                  </div>
                </div>
              </el-col>
            </el-row>

            <!-- 历史记录 -->
            <el-divider content-position="left">操作历史</el-divider>
            <el-table :data="rotationHistory" size="small" border v-loading="historyLoading">
              <el-table-column prop="action" label="操作" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="getActionType(row.action)">{{ getActionLabel(row.action) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="80">
                <template #default="{ row }">
                  <el-tag size="small" :type="row.status === 'success' ? 'success' : row.status === 'partial' ? 'warning' : 'danger'">
                    {{ row.status === 'success' ? '成功' : row.status === 'partial' ? '部分' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="migrated_records" label="迁移数" width="80" align="center" />
              <el-table-column prop="error_message" label="错误原因" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  <span v-if="row.error_message" class="text-danger">{{ row.error_message }}</span>
                  <span v-else class="text-muted">-</span>
                </template>
              </el-table-column>
              <el-table-column prop="created_at" label="时间" width="160">
                <template #default="{ row }">
                  {{ formatTime(row.created_at) }}
                </template>
              </el-table-column>
            </el-table>
          </div>

          <!-- JWT 密钥轮换区块 -->
          <el-divider content-position="left">
            <el-icon><Key /></el-icon> JWT 密钥轮换
          </el-divider>
          
          <div class="key-rotation-section" v-loading="jwtRotationLoading">
            <!-- JWT 密钥版本列表 -->
            <el-card shadow="never" style="margin-bottom: 20px;">
              <template #header>
                <div class="card-header">
                  <span>JWT 密钥版本</span>
                  <el-space>
                    <el-button type="primary" size="small" @click="handleJwtGenerateKey" :loading="jwtGenerating">
                      <el-icon><Plus /></el-icon> 生成新密钥
                    </el-button>
                    <el-button type="warning" size="small" @click="handleJwtFullRotation" :loading="jwtRotationLoading">
                      <el-icon><Refresh /></el-icon> 一键轮换
                    </el-button>
                  </el-space>
                </div>
              </template>
              <el-table :data="jwtRotationData.keys || []" size="small" border>
                <el-table-column prop="key_id" label="版本" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag :type="row.key_id === jwtRotationData.current_version ? 'success' : 'info'" size="small">
                      {{ row.key_id.toUpperCase() }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="key_value_preview" label="密钥预览">
                  <template #default="{ row }">
                    <code>{{ row.key_value_preview }}</code>
                  </template>
                </el-table-column>
                <el-table-column prop="is_active" label="当前版本" width="100" align="center">
                  <template #default="{ row }">
                    <el-tag v-if="row.key_id === jwtRotationData.current_version" type="success">当前</el-tag>
                    <el-tag v-else type="info">-</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="created_at" label="创建时间" width="160">
                  <template #default="{ row }">
                    {{ formatTime(row.created_at) }}
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" align="center">
                  <template #default="{ row }">
                    <el-button 
                      v-if="row.key_id !== jwtRotationData.current_version"
                      type="primary" 
                      size="small" 
                      link
                      @click="handleJwtSwitchVersion(row.key_id)"
                      :loading="jwtSwitching">
                      切换
                    </el-button>
                    <span v-else class="text-muted">-</span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>

            <el-alert type="info" :closable="false" show-icon style="margin-top: 16px;">
              <template #title>
                JWT 密钥用于签发用户访问令牌。切换版本后，旧密钥签发的令牌在过期前仍可验证。
              </template>
            </el-alert>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- 插件管理 -->
      <el-tab-pane label="插件管理" name="plugins">
        <template #label>
          <span class="tab-label"><el-icon><Box /></el-icon>插件管理</span>
        </template>
        <el-card shadow="never" style="min-height: 500px;">
          <PluginsView />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { systemApi } from '@/api/system'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  DataAnalysis, Timer, Setting, Coin, Folder, Cloudy, Files, Lock, 
  Refresh, RefreshLeft, Box, Key 
} from '@element-plus/icons-vue'
import { getAwsRegionsGrouped } from '@/api/awsRegions'
import * as rotationApi from '@/api/keyRotation'
import * as jwtRotationApi from '@/api/jwtRotation'
import dayjs from 'dayjs'
import PluginsView from './plugins.vue'
import router from '@/router'

// Tab 状态
const activeTab = ref('overview')

// ==================== 系统概览 ====================
const overview = reactive({
  version: '-',
  python_version: '-',
  database_type: '-',
  storage_type: '-',
  redis_enabled: false,
  scheduler_running: false
})

const loadOverview = async () => {
  try {
    const data = await systemApi.getOverview()
    Object.assign(overview, data)
  } catch (error) {
    console.error('加载系统概览失败:', error)
  }
}

// ==================== 后台任务 ====================
const schedulerOverview = ref({})
const schedulerJobs = ref([])
const schedulerLoading = ref(false)
const runningJobs = computed(() => schedulerOverview.value.running_jobs || 0)
let schedulerTimer = null

// 密钥版本显示（倒序，最多10个）
const displayKeyVersions = computed(() => {
  return [...keyVersions.value].sort((a, b) => b.id - a.id).slice(0, 10)
})
const deletingKey = ref(null)

const fetchSchedulerOverview = async () => {
  schedulerLoading.value = true
  try {
    const res = await request.get('/scheduler/overview')
    schedulerOverview.value = res || {}
    const approvalJobs = res?.approval_scheduler?.jobs || []
    const taskJobs = res?.task_scheduler?.jobs || []
    schedulerJobs.value = [...approvalJobs, ...taskJobs]
  } catch (error) {
    console.error('获取调度器状态失败:', error)
  } finally {
    schedulerLoading.value = false
  }
}

const handleJobAction = async (job, action) => {
  if (action === 'trigger') {
    try {
      await ElMessageBox.confirm(`确定要立即执行任务 "${job.name || job.id}" 吗？`, '确认执行', { type: 'warning' })
    } catch { return }
  }
  job._actionLoading = true
  try {
    await request.post(`/scheduler/jobs/${job.id}/action`, { action })
    ElMessage.success(`任务已${action === 'pause' ? '暂停' : action === 'resume' ? '恢复' : '执行'}`)
    fetchSchedulerOverview()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    job._actionLoading = false
  }
}

const getTaskTypeStyle = (type) => ({ approval: 'primary', scheduled: 'success', system: 'warning' }[type] || 'info')
const getTaskTypeLabel = (type) => ({ approval: '审批', scheduled: '定时', system: '系统' }[type] || type)
const getTriggerTypeLabel = (type) => ({ cron: 'Cron', interval: '间隔', date: '定时' }[type] || type)

// ==================== 数据库配置 ====================
const databaseConfigs = ref([])

const loadDatabaseConfig = async () => {
  try {
    const data = await systemApi.getDatabaseConfig()
    databaseConfigs.value = (data.items || []).map(item => ({ ...item, saving: false }))
  } catch (error) {
    console.error('加载数据库配置失败:', error)
  }
}

const handleDbConfigChange = async (row) => {
  row.saving = true
  try {
    await systemApi.updateDatabaseConfig(row.db_type, { enabled: row.enabled })
    ElMessage.success(`${row.display_name} 已${row.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    row.enabled = !row.enabled
    ElMessage.error('更新失败')
  } finally {
    row.saving = false
  }
}

const getDbIcon = (dbType) => Coin
const getDbColor = (dbType) => ({ mysql: '#4479A1', postgresql: '#336791', redis: '#DC382D' }[dbType] || '#909399')

// ==================== AWS 配置 ====================
const awsRegionGroups = ref([])
const awsRegionsLoading = ref(false)
const awsConfig = reactive({ aws_access_key_id: '', aws_secret_access_key: '', aws_region: 'us-east-1' })
const savingAws = ref(false)
const testingAws = ref(false)

const fetchAwsRegions = async () => {
  awsRegionsLoading.value = true
  try { awsRegionGroups.value = await getAwsRegionsGrouped(true) } 
  finally { awsRegionsLoading.value = false }
}

const saveAwsConfig = async () => {
  savingAws.value = true
  try {
    await systemApi.updateStorageConfig({
      s3_access_key_id: awsConfig.aws_access_key_id,
      s3_secret_access_key: awsConfig.aws_secret_access_key,
      s3_region: awsConfig.aws_region
    })
    ElMessage.success('AWS 凭证配置已保存')
  } catch { ElMessage.error('保存失败') }
  finally { savingAws.value = false }
}

const testAwsConfig = async () => {
  testingAws.value = true
  try {
    const result = await systemApi.testAwsConnection(awsConfig)
    ElMessage[result.success ? 'success' : 'error'](result.message)
  } catch (error) {
    ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    testingAws.value = false
  }
}

const resetAwsConfig = () => {
  awsConfig.aws_access_key_id = ''
  awsConfig.aws_secret_access_key = ''
  awsConfig.aws_region = 'us-east-1'
}

// ==================== 存储配置 ====================
const storageConfig = reactive({
  storage_type: 'local', retention_days: 30, size_threshold: 10000000, local_path: '/app/data/sql_files',
  s3_bucket: '', s3_region: '', s3_endpoint: '', s3_access_key_id: '', s3_secret_access_key: '',
  oss_bucket: '', oss_endpoint: '', oss_access_key_id: '', oss_access_key_secret: ''
})
const saving = ref(false)
const testing = ref(false)

const loadStorageConfig = async () => {
  try {
    const data = await systemApi.getStorageConfig()
    Object.assign(storageConfig, data)
    awsConfig.aws_access_key_id = data.s3_access_key_id || ''
    awsConfig.aws_secret_access_key = data.s3_secret_access_key || ''
    awsConfig.aws_region = data.s3_region || 'us-east-1'
  } catch (error) {
    console.error('加载存储配置失败:', error)
  }
}

const saveStorageConfig = async () => {
  saving.value = true
  try {
    const result = await systemApi.updateStorageConfig(storageConfig)
    ElMessage.success(result.message)
    if (result.requires_restart) ElMessage.warning('部分配置需要重启服务后生效')
  } catch { ElMessage.error('保存失败') }
  finally { saving.value = false }
}

const testStorageConfig = async () => {
  testing.value = true
  try {
    const result = await systemApi.testStorageConfig(storageConfig)
    ElMessage[result.success ? 'success' : 'error'](result.message)
  } catch { ElMessage.error('测试失败') }
  finally { testing.value = false }
}

// ==================== 安全配置 ====================
const securityConfig = reactive({
  jwt_configured: false, jwt_secret_key: '', aes_configured: false, aes_key: '', token_expire_hours: 24
})

// 密钥轮换统计
const overviewData = ref({
  current_version: '',
  total_keys: 0,
  total_records: 0,
  latest_key_created_at: null
})
const rotationConfig = ref({
  enabled: false,
  schedule_type: 'monthly',
  schedule_day: 1,
  schedule_time: '02:00',
  schedule_quarter_month: 1,
  auto_switch: false
})
const rotationTime = ref('02:00')
const keyVersions = ref([])  // 所有密钥版本
const rotationHistory = ref([])
const rotationLoading = ref(false)
const switching = ref(false)
const generatingKey = ref(false)
const historyLoading = ref(false)

// ==================== JWT 密钥轮换 ====================
const jwtRotationData = ref({
  current_version: '',
  total_keys: 0,
  last_rotation_at: null,
  keys: []
})
const jwtRotationLoading = ref(false)
const jwtSwitching = ref(false)
const jwtGenerating = ref(false)

const loadRotationStatus = async () => {
  rotationLoading.value = true
  try {
    const [overview, versions, config] = await Promise.all([
      rotationApi.getKeyRotationStatus(),
      rotationApi.getKeyVersions(),
      rotationApi.getRotationConfig()
    ])
    overviewData.value = {
      current_version: overview.current_version || versions.current_version,
      total_keys: versions.total_versions,
      total_records: overview.unrotated_count || 0,
      latest_key_created_at: null
    }
    keyVersions.value = versions.versions || []
    rotationConfig.value = {
      enabled: config.enabled,
      schedule_type: config.schedule_type,
      schedule_day: config.schedule_day,
      schedule_time: config.schedule_time,
      schedule_quarter_month: 1,
      auto_switch: config.auto_switch
    }
    rotationTime.value = config.schedule_time
  } catch (error) {
    console.error('加载密钥轮换状态失败:', error)
  } finally {
    rotationLoading.value = false
  }
}

const loadRotationHistory = async () => {
  historyLoading.value = true
  try {
    const result = await rotationApi.getRotationHistory(1, 10)
    rotationHistory.value = result.logs || []
  } catch (error) {
    console.error('加载历史记录失败:', error)
  } finally {
    historyLoading.value = false
  }
}

const loadRotationData = async () => {
  console.log('开始加载密钥轮换数据...')
  try {
    const results = await Promise.all([
      loadRotationStatus(),
      loadRotationHistory()
    ])
    console.log('密钥轮换数据加载完成', results)
  } catch (error) {
    console.error('加载密钥轮换数据失败:', error)
  }
}

// JWT 密钥轮换
const loadJwtRotationStatus = async () => {
  jwtRotationLoading.value = true
  try {
    const data = await jwtRotationApi.getJwtRotationStatus()
    jwtRotationData.value = data
  } catch (error) {
    console.error('加载 JWT 轮换状态失败:', error)
  } finally {
    jwtRotationLoading.value = false
  }
}

const handleJwtGenerateKey = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要生成新的 JWT 密钥吗？\n\n生成后，新登录用户将使用新密钥签发令牌。',
      '生成 JWT 密钥',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    jwtGenerating.value = true
    const result = await jwtRotationApi.generateJwtKey()
    ElMessage.success(`新 JWT 密钥已生成`)
    await loadJwtRotationStatus()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '生成失败')
    }
  } finally {
    jwtGenerating.value = false
  }
}

const handleJwtSwitchVersion = async (targetVersion) => {
  try {
    await ElMessageBox.confirm(
      `确定切换到 ${targetVersion.toUpperCase()} 版本吗？\n\n新登录用户将使用新密钥签发令牌。`,
      '确认切换',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    jwtSwitching.value = true
    const result = await jwtRotationApi.switchJwtVersion(targetVersion)
    ElMessage.success(result.message)
    await loadJwtRotationStatus()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('切换失败')
    }
  } finally {
    jwtSwitching.value = false
  }
}

const handleJwtFullRotation = async () => {
  try {
    await ElMessageBox.confirm(
      '确定执行一键轮换吗？\n\n将生成新密钥并自动切换。',
      '一键轮换',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    jwtRotationLoading.value = true
    const result = await jwtRotationApi.fullJwtRotation()
    ElMessage.success(`一键轮换完成，新版本: ${result.new_version}`)
    await loadJwtRotationStatus()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '轮换失败')
    }
  } finally {
    jwtRotationLoading.value = false
  }
}

const handleConfigChange = async () => {
  try {
    await rotationApi.updateRotationConfig({
      enabled: rotationConfig.value.enabled,
      schedule_type: rotationConfig.value.schedule_type,
      schedule_day: rotationConfig.value.schedule_day,
      schedule_time: rotationTime.value,
      auto_switch: rotationConfig.value.auto_switch
    })
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('配置保存失败')
  }
}

const handleSwitchVersion = async (targetVersion) => {
  console.log('1. 点击了切换按钮, 目标版本:', targetVersion)
  try {
    const confirmed = await ElMessageBox.confirm(
      `确定要切换到 ${targetVersion.toUpperCase()} 版本吗？\n\n切换后，新加密的数据将使用新密钥。旧密钥加密的数据仍可自动解密。`,
      '确认切换',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    console.log('2. 用户确认了, confirmed:', confirmed)
    switching.value = true
    console.log('3. 开始调用 API')
    const result = await rotationApi.switchKeyVersion(targetVersion)
    console.log('4. API 返回:', result)
    ElMessage.success(`已切换到 ${targetVersion.toUpperCase()} 版本`)
    await loadRotationData()
  } catch (error) {
    console.error('5. 捕获到错误:', error)
    console.error('   error 类型:', typeof error)
    console.error('   error === cancel:', error === 'cancel')
    console.error('   error.response:', error?.response)
    if (error !== 'cancel' && error !== 'close') {
      ElMessage.error('切换失败: ' + (error?.message || error?.detail || String(error)))
    }
  } finally {
    switching.value = false
  }
}

const handleGenerateKey = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要生成新的密钥版本吗？\n\n生成后，您可以执行迁移和切换版本。',
      '生成新密钥',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    generatingKey.value = true
    const result = await rotationApi.generateNewKey()
    ElMessage.success(`新密钥版本 ${result.new_version.toUpperCase()} 已生成`)
    await loadRotationData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '生成密钥失败')
    }
  } finally {
    generatingKey.value = false
  }
}

const handleDeleteKey = async (keyId) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除密钥版本 ${keyId.toUpperCase()} 吗？\n\n删除后无法恢复，请谨慎操作。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'danger' }
    )
    deletingKey.value = keyId
    await rotationApi.deleteKeyVersion(keyId)
    ElMessage.success(`密钥版本 ${keyId.toUpperCase()} 已删除`)
    await loadRotationStatus()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  } finally {
    deletingKey.value = null
  }
}

const getActionType = (action) => {
  const map = { preview: 'info', migrate: 'warning', switch: 'success', delete: 'danger' }
  return map[action] || 'info'
}

const getActionLabel = (action) => {
  const map = { preview: '预览', migrate: '迁移', switch: '切换', delete: '删除' }
  return map[action] || action
}

const loadSecurityConfig = async () => {
  try {
    const data = await systemApi.getSecurityConfig()
    Object.assign(securityConfig, data)
  } catch (error) {
    console.error('加载安全配置失败:', error)
  }
}

// ==================== 工具函数 ====================
const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'

onMounted(() => {
  loadOverview()
  fetchSchedulerOverview()
  loadDatabaseConfig()
  loadStorageConfig()
  loadSecurityConfig()
  fetchAwsRegions()
  // 加载密钥轮换数据
  loadRotationData()
  // 加载 JWT 轮换状态
  loadJwtRotationStatus()
  // 每30秒刷新调度器状态
  schedulerTimer = setInterval(fetchSchedulerOverview, 30000)
})

onUnmounted(() => {
  if (schedulerTimer) clearInterval(schedulerTimer)
})
</script>

<style lang="scss" scoped>
.system-settings {
  .settings-tabs {
    background: white;
    padding: 20px;
    border-radius: 8px;
  }
  
  .tab-label {
    display: flex;
    align-items: center;
    gap: 6px;
    
    .el-icon { font-size: 16px; }
    
    .tab-badge {
      margin-left: 4px;
      :deep(.el-badge__content) { font-size: 10px; height: 14px; line-height: 14px; padding: 0 4px; }
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .overview-card { max-width: 800px; }

  .db-type-cell {
    display: flex;
    align-items: center;
    gap: 12px;
    .db-info {
      .db-name { font-weight: 600; }
      .db-desc { font-size: 12px; color: #909399; }
    }
  }

  .hint {
    font-size: 12px;
    color: #909399;
    margin-left: 8px;
    &.success { color: #67c23a; }
    &.warning { color: #e6a23c; }
  }

  .unit { margin-left: 10px; color: #909399; }

  .secret-value {
    display: flex;
    align-items: center;
    code {
      background: #f5f7fa;
      padding: 6px 12px;
      border-radius: 4px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      border: 1px solid #e4e7ed;
    }
  }
  
  // 调度器状态卡片
  .status-card { height: 100%; }
  .status-header { display: flex; align-items: center; gap: 16px; }
  .status-icon { font-size: 48px; color: #909399; &.running { color: #67c23a; } }
  .status-info { flex: 1; }
  .status-title { font-size: 18px; font-weight: 600; margin-bottom: 8px; }
  .status-badge { display: flex; align-items: center; gap: 10px; }
  .job-count { color: #909399; font-size: 14px; }
  .summary-stats { display: flex; gap: 20px; }
  .stat-item { display: flex; flex-direction: column; align-items: center; }
  .stat-label { font-size: 12px; color: #909399; }
  .stat-value { font-size: 20px; font-weight: 600; &.running { color: #67c23a; } &.paused { color: #e6a23c; } }
  
  .job-id { font-size: 12px; background: #f5f7fa; padding: 2px 6px; border-radius: 4px; }
  
  // 密钥轮换区块
  .key-rotation-section {
    margin-top: 20px;
    
    .rotation-stats {
      margin-bottom: 20px;
    }
    
    .rotation-stat-card {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px;
      background: #f5f7fa;
      border-radius: 8px;
      
      .stat-icon {
        width: 40px;
        height: 40px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: white;
        
        &.current { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        &.total { background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }
        &.pending { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        &.v2 { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
      }
      
      .stat-info {
        flex: 1;
        
        .stat-label {
          font-size: 12px;
          color: #909399;
          margin-bottom: 4px;
        }
        
        .stat-value {
          font-size: 20px;
          font-weight: 600;
          color: #303133;
        }
      }
    }
    
    .version-cell {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 4px;
    }
    
    .rotation-form {
      margin-bottom: 20px;
      
      .form-tip {
        margin-left: 10px;
        font-size: 12px;
        color: #909399;
      }
    }
    
    .migration-table {
      margin-bottom: 16px;
    }
    
    .rotation-actions {
      display: flex;
      gap: 12px;
      margin-bottom: 20px;
      justify-content: center;
    }
  }

  .job-name { display: flex; flex-direction: column; .job-desc { font-size: 12px; color: #909399; margin-top: 2px; } }
  .trigger-info { display: flex; flex-direction: column; gap: 4px; .trigger-config { font-size: 12px; color: #909399; } }
  .text-muted { color: #c0c4cc; }
  .text-danger { color: #f56c6c; font-size: 12px; }
}

// 强制覆盖 Element Plus 表格截断样式
:deep(.el-table) {
  .el-table__cell { text-overflow: unset !important; overflow: visible !important; }
  .cell { text-overflow: unset !important; overflow: visible !important; white-space: normal !important; }
  .el-tag { white-space: nowrap !important; }
}
</style>
