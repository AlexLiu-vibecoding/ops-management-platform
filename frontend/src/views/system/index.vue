<template>
  <div class="system-settings">
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 系统概览 -->
      <el-tab-pane label="系统概览" name="overview">
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

      <!-- 数据库类型配置 -->
      <el-tab-pane label="数据库类型" name="database">
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
              <template #default="{ row }">
                <el-tag type="info">{{ row.default_port }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  :loading="row.saving"
                  @change="handleDbConfigChange(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="说明">
              <template #default="{ row }">
                <span v-if="row.enabled" class="hint success">
                  用户在添加实例时可以选择此数据库类型
                </span>
                <span v-else class="hint warning">
                  已禁用，用户无法添加此类型的实例
                </span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 存储配置 -->
      <el-tab-pane label="存储配置" name="storage">
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
                <el-radio label="local">
                  <el-icon><Folder /></el-icon>
                  本地存储
                </el-radio>
                <el-radio label="s3">
                  <el-icon><Cloudy /></el-icon>
                  AWS S3
                </el-radio>
                <el-radio label="oss">
                  <el-icon><Files /></el-icon>
                  阿里云 OSS
                </el-radio>
              </el-radio-group>
            </el-form-item>

            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="文件保留天数">
                  <el-input-number
                    v-model="storageConfig.retention_days"
                    :min="1"
                    :max="365"
                  />
                  <span class="unit">天</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="大文件阈值">
                  <el-input-number
                    v-model="storageConfig.size_threshold"
                    :min="1000"
                    :max="1000000"
                    :step="1000"
                  />
                  <span class="unit">字符 (约 {{ (storageConfig.size_threshold / 1000).toFixed(0) }}KB)</span>
                </el-form-item>
              </el-col>
            </el-row>

            <!-- 本地存储配置 -->
            <template v-if="storageConfig.storage_type === 'local'">
              <el-divider content-position="left">本地存储配置</el-divider>
              <el-form-item label="存储路径">
                <el-input
                  v-model="storageConfig.local_path"
                  placeholder="/app/data/sql_files"
                >
                  <template #prepend>
                    <el-icon><Folder /></el-icon>
                  </template>
                </el-input>
                <div class="hint">大SQL文件将保存到此目录</div>
              </el-form-item>
            </template>

            <!-- AWS S3 配置 -->
            <template v-if="storageConfig.storage_type === 's3'">
              <el-divider content-position="left">AWS S3 配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Bucket 名称">
                    <el-input v-model="storageConfig.s3_bucket" placeholder="my-sql-files" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="区域">
                    <el-input v-model="storageConfig.s3_region" placeholder="us-east-1" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-form-item label="端点URL">
                <el-input
                  v-model="storageConfig.s3_endpoint"
                  placeholder="可选，用于兼容 S3 的其他服务"
                />
                <div class="hint">留空使用 AWS 默认端点</div>
              </el-form-item>
              <el-divider content-position="left">AWS 凭证</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Access Key ID">
                    <el-input 
                      v-model="storageConfig.s3_access_key_id" 
                      placeholder="AKIAIOSFODNN7EXAMPLE"
                      show-password
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Secret Access Key">
                    <el-input 
                      v-model="storageConfig.s3_secret_access_key" 
                      placeholder="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
                      show-password
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="hint" style="margin-left: 140px;">AWS 凭证也可通过环境变量 AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY 配置</div>
            </template>

            <!-- 阿里云 OSS 配置 -->
            <template v-if="storageConfig.storage_type === 'oss'">
              <el-divider content-position="left">阿里云 OSS 配置</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Bucket 名称">
                    <el-input v-model="storageConfig.oss_bucket" placeholder="my-sql-files" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Endpoint">
                    <el-input v-model="storageConfig.oss_endpoint" placeholder="oss-cn-hangzhou.aliyuncs.com" />
                  </el-form-item>
                </el-col>
              </el-row>
              <el-divider content-position="left">OSS 凭证</el-divider>
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="Access Key ID">
                    <el-input 
                      v-model="storageConfig.oss_access_key_id" 
                      placeholder="LTAI4xxx..."
                      show-password
                    />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="Access Key Secret">
                    <el-input 
                      v-model="storageConfig.oss_access_key_secret" 
                      placeholder="xxx..."
                      show-password
                    />
                  </el-form-item>
                </el-col>
              </el-row>
              <div class="hint" style="margin-left: 140px;">OSS 凭证也可通过环境变量 OSS_ACCESS_KEY_ID / OSS_ACCESS_KEY_SECRET 配置</div>
            </template>

            <el-form-item>
              <el-button type="primary" @click="saveStorageConfig" :loading="saving">
                保存配置
              </el-button>
              <el-button @click="testStorageConfig" :loading="testing">
                测试连接
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>

      <!-- 安全配置 -->
      <el-tab-pane label="安全配置" name="security">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>安全配置</span>
              <el-tag type="danger" size="small">敏感信息，请妥善保管</el-tag>
            </div>
          </template>

          <el-alert
            title="安全提示"
            type="warning"
            :closable="false"
            show-icon
            style="margin-bottom: 20px;"
          >
            以下密钥用于系统安全加密，请勿泄露。如需修改，请在服务器环境变量中配置。
          </el-alert>

          <el-descriptions :column="1" border>
            <el-descriptions-item label="JWT 密钥">
              <div class="secret-value">
                <code>{{ securityConfig.jwt_secret_key }}</code>
                <el-tag :type="securityConfig.jwt_configured ? 'success' : 'warning'" size="small" style="margin-left: 10px;">
                  {{ securityConfig.jwt_configured ? '已自定义' : '使用默认值' }}
                </el-tag>
              </div>
              <div class="hint">用于签名 JWT Token，环境变量: JWT_SECRET_KEY</div>
            </el-descriptions-item>
            <el-descriptions-item label="AES 密钥">
              <div class="secret-value">
                <code>{{ securityConfig.aes_key }}</code>
                <el-tag :type="securityConfig.aes_configured ? 'success' : 'warning'" size="small" style="margin-left: 10px;">
                  {{ securityConfig.aes_configured ? '已自定义' : '使用默认值' }}
                </el-tag>
              </div>
              <div class="hint">用于加密敏感数据，必须32字符，环境变量: AES_KEY</div>
            </el-descriptions-item>
            <el-descriptions-item label="密码加盐">
              <div class="secret-value">
                <code>{{ securityConfig.password_salt }}</code>
              </div>
              <div class="hint">用于密码哈希加盐，环境变量: PASSWORD_SALT</div>
            </el-descriptions-item>
            <el-descriptions-item label="Token 有效期">
              <el-tag type="primary">{{ securityConfig.token_expire_hours }} 小时</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="密码策略">
              <el-tag v-if="securityConfig.password_policy?.min_length">
                最少 {{ securityConfig.password_policy.min_length }} 位
              </el-tag>
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">环境变量配置示例</el-divider>
          
          <el-input
            type="textarea"
            :rows="6"
            readonly
            :model-value="envExample"
            style="font-family: monospace;"
          />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { systemApi } from '@/api/system'
import { ElMessage } from 'element-plus'
import { Coin, Folder, Cloudy, Files } from '@element-plus/icons-vue'

const activeTab = ref('overview')
const saving = ref(false)
const testing = ref(false)

// 系统概览
const overview = reactive({
  version: '-',
  python_version: '-',
  database_type: '-',
  storage_type: '-',
  redis_enabled: false,
  scheduler_running: false
})

// 数据库配置
const databaseConfigs = ref([])

// 存储配置
const storageConfig = reactive({
  storage_type: 'local',
  retention_days: 30,
  size_threshold: 10000,
  local_path: '/app/data/sql_files',
  // AWS S3 配置
  s3_bucket: '',
  s3_region: '',
  s3_endpoint: '',
  s3_access_key_id: '',
  s3_secret_access_key: '',
  // 阿里云 OSS 配置
  oss_bucket: '',
  oss_endpoint: '',
  oss_access_key_id: '',
  oss_access_key_secret: ''
})

// 安全配置
const securityConfig = reactive({
  jwt_configured: false,
  jwt_secret_key: '',
  aes_configured: false,
  aes_key: '',
  password_salt: '',
  token_expire_hours: 24,
  password_policy: {}
})

// 环境变量示例
const envExample = computed(() => {
  return `# JWT 密钥 (至少32字符)
JWT_SECRET_KEY=your-jwt-secret-key-at-least-32-chars

# AES 加密密钥 (必须32字符)
AES_KEY=your-aes-key-must-be-32-characters!!

# 密码加密盐
PASSWORD_SALT=your-password-salt`
})

// 获取数据库图标
const getDbIcon = (dbType) => {
  const icons = {
    mysql: Coin,
    postgresql: Coin,
    redis: Coin
  }
  return icons[dbType] || Coin
}

// 获取数据库颜色
const getDbColor = (dbType) => {
  const colors = {
    mysql: '#4479A1',
    postgresql: '#336791',
    redis: '#DC382D'
  }
  return colors[dbType] || '#909399'
}

// 加载系统概览
const loadOverview = async () => {
  try {
    const data = await systemApi.getOverview()
    Object.assign(overview, data)
  } catch (error) {
    console.error('加载系统概览失败:', error)
  }
}

// 加载数据库配置
const loadDatabaseConfig = async () => {
  try {
    const data = await systemApi.getDatabaseConfig()
    databaseConfigs.value = data.items.map(item => ({
      ...item,
      saving: false
    }))
  } catch (error) {
    console.error('加载数据库配置失败:', error)
  }
}

// 处理数据库配置变更
const handleDbConfigChange = async (row) => {
  row.saving = true
  try {
    await systemApi.updateDatabaseConfig(row.db_type, {
      enabled: row.enabled
    })
    ElMessage.success(`${row.display_name} 已${row.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    row.enabled = !row.enabled
    ElMessage.error('更新失败')
  } finally {
    row.saving = false
  }
}

// 加载存储配置
const loadStorageConfig = async () => {
  try {
    const data = await systemApi.getStorageConfig()
    Object.assign(storageConfig, data)
  } catch (error) {
    console.error('加载存储配置失败:', error)
  }
}

// 保存存储配置
const saveStorageConfig = async () => {
  saving.value = true
  try {
    const result = await systemApi.updateStorageConfig(storageConfig)
    ElMessage.success(result.message)
    if (result.requires_restart) {
      ElMessage.warning('部分配置需要重启服务后生效')
    }
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 测试存储配置
const testStorageConfig = async () => {
  testing.value = true
  try {
    const result = await systemApi.testStorageConfig(storageConfig)
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

// 加载安全配置
const loadSecurityConfig = async () => {
  try {
    const data = await systemApi.getSecurityConfig()
    Object.assign(securityConfig, data)
  } catch (error) {
    console.error('加载安全配置失败:', error)
  }
}

onMounted(() => {
  loadOverview()
  loadDatabaseConfig()
  loadStorageConfig()
  loadSecurityConfig()
})
</script>

<style lang="scss" scoped>
.system-settings {
  .settings-tabs {
    background: white;
    padding: 20px;
    border-radius: 8px;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .overview-card {
    max-width: 800px;
  }

  .db-type-cell {
    display: flex;
    align-items: center;
    gap: 12px;

    .db-info {
      .db-name {
        font-weight: 600;
      }
      .db-desc {
        font-size: 12px;
        color: #909399;
      }
    }
  }

  .hint {
    font-size: 12px;
    color: #909399;
    margin-left: 8px;

    &.success {
      color: #67c23a;
    }

    &.warning {
      color: #e6a23c;
    }
  }

  .unit {
    margin-left: 10px;
    color: #909399;
  }

  .secret-value {
    display: flex;
    align-items: center;
    
    code {
      background: #f5f7fa;
      padding: 6px 12px;
      border-radius: 4px;
      font-family: 'Consolas', 'Monaco', monospace;
      font-size: 13px;
      color: #303133;
      word-break: break-all;
      border: 1px solid #e4e7ed;
    }
  }
}
</style>
