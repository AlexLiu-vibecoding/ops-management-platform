<template>
  <div class="key-rotation-container">
    <div class="page-header">
      <h2>密钥轮换管理</h2>
      <p class="subtitle">管理 AES 加密密钥版本，支持自动轮换和数据迁移</p>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon version-icon">
              <el-icon><Key /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">当前版本</div>
              <div class="stat-value">{{ statusData?.current_version?.toUpperCase() || 'v1' }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon total-icon">
              <el-icon><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">加密记录总数</div>
              <div class="stat-value">{{ statistics?.total || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon pending-icon">
              <el-icon><Warning /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">待迁移</div>
              <div class="stat-value">{{ statistics?.needs_migration || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon v2-icon">
              <el-icon><CircleCheck /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-label">V2 版本</div>
              <div class="stat-value">{{ statistics?.v2_count || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主内容区域 -->
    <el-row :gutter="20" class="main-content">
      <!-- 左侧：配置面板 -->
      <el-col :span="14">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Setting /></el-icon> 密钥配置</span>
            </div>
          </template>

          <!-- 密钥版本状态 -->
          <div class="version-status">
            <div class="version-item">
              <el-tag :type="versionInfo?.v1_configured ? 'success' : 'info'" size="large">
                <el-icon v-if="versionInfo?.v1_configured"><Check /></el-icon>
                <el-icon v-else><Close /></el-icon>
                V1: {{ versionInfo?.v1_configured ? versionInfo.v1_key_preview : '未配置' }}
              </el-tag>
            </div>
            <div class="version-item">
              <el-tag :type="versionInfo?.v2_configured ? 'success' : 'info'" size="large">
                <el-icon v-if="versionInfo?.v2_configured"><Check /></el-icon>
                <el-icon v-else><Close /></el-icon>
                V2: {{ versionInfo?.v2_configured ? versionInfo.v2_key_preview : '未配置' }}
              </el-tag>
            </div>
          </div>

          <!-- 自动轮换配置 -->
          <el-divider content-position="left">自动轮换配置</el-divider>
          
          <el-form :model="configForm" label-width="120px" class="config-form">
            <el-form-item label="启用自动轮换">
              <el-switch v-model="configForm.enabled" @change="handleConfigChange" />
            </el-form-item>
            
            <el-form-item label="轮换周期">
              <el-select v-model="configForm.schedule_type" @change="handleConfigChange" style="width: 100%">
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
                <el-option label="每季度" value="quarterly" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="执行时间">
              <el-time-picker 
                v-model="configForm.schedule_time" 
                format="HH:mm" 
                value-format="HH:mm"
                @change="handleConfigChange"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item :label="scheduleDayLabel">
              <el-input-number 
                v-model="configForm.schedule_day" 
                :min="scheduleDayMin" 
                :max="scheduleDayMax"
                @change="handleConfigChange"
                style="width: 100%"
              />
            </el-form-item>
            
            <el-form-item label="迁移后自动切换">
              <el-switch v-model="configForm.auto_switch" @change="handleConfigChange" />
              <div class="form-tip">执行迁移后自动切换到新密钥版本</div>
            </el-form-item>
          </el-form>

          <!-- 迁移预览 -->
          <el-divider content-position="left">数据迁移</el-divider>
          
          <div class="migration-preview" v-loading="previewLoading">
            <el-table :data="previewTables" size="small" border>
              <el-table-column prop="description" label="数据项" />
              <el-table-column prop="total" label="总数" width="80" align="center" />
              <el-table-column prop="v1_or_legacy" label="待迁移" width="80" align="center">
                <template #default="{ row }">
                  <el-tag type="warning" size="small">{{ row.v1_or_legacy }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="v2" label="已完成" width="80" align="center">
                <template #default="{ row }">
                  <el-tag type="success" size="small">{{ row.v2 }}</el-tag>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="preview-summary">
              共 {{ totalRecords }} 条记录，其中 {{ totalNeedsMigration }} 条需要迁移
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="action-buttons">
            <el-button type="primary" @click="handlePreview" :loading="previewLoading">
              <el-icon><Refresh /></el-icon> 刷新预览
            </el-button>
            <el-button type="warning" @click="handleMigrate" :disabled="!statusData?.can_rotate || totalNeedsMigration === 0" :loading="migrateLoading">
              <el-icon><Upload /></el-icon> 执行迁移
            </el-button>
            <el-button type="success" @click="handleSwitchVersion" :disabled="!statusData?.can_rotate" :loading="switchLoading">
              <el-icon><Switch /></el-icon> 切换版本
            </el-button>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：历史记录 -->
      <el-col :span="10">
        <el-card class="history-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><Clock /></el-icon> 操作历史</span>
              <el-button text @click="loadHistory">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>

          <el-table :data="historyLogs" size="small" v-loading="historyLoading">
            <el-table-column prop="action" label="操作" width="80">
              <template #default="{ row }">
                <el-tag size="small" :type="getActionType(row.action)">
                  {{ getActionLabel(row.action) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="70">
              <template #default="{ row }">
                <el-tag size="small" :type="row.status === 'success' ? 'success' : 'danger'">
                  {{ row.status === 'success' ? '成功' : '失败' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="migrated_records" label="迁移数" width="70" align="center" />
            <el-table-column prop="created_at" label="时间" width="140">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-if="historyTotal > pageSize"
            class="history-pagination"
            layout="prev, pager, next"
            :total="historyTotal"
            :page-size="pageSize"
            v-model:current-page="currentPage"
            @current-change="loadHistory"
          />
        </el-card>

        <!-- 下次轮换时间 -->
        <el-card class="next-rotation-card" v-if="configData?.enabled">
          <template #header>
            <div class="card-header">
              <span><el-icon><Timer /></el-icon> 下次自动轮换</span>
            </div>
          </template>
          <div class="next-rotation-time">
            <el-icon class="time-icon"><Calendar /></el-icon>
            <span>{{ nextRotationDisplay }}</span>
          </div>
          <el-button type="primary" text @click="handleTriggerAutoRotation" :loading="autoRotateLoading">
            立即执行
          </el-button>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Key, Document, Warning, CircleCheck, Setting, Check, Close,
  Refresh, Upload, Switch, Clock, Timer, Calendar
} from '@element-plus/icons-vue'
import * as api from '@/api/keyRotation'

// 状态数据
const statusData = ref(null)
const versionInfo = ref(null)
const statistics = ref(null)
const configData = ref(null)
const previewTables = ref([])
const historyLogs = ref([])

// 加载状态
const previewLoading = ref(false)
const migrateLoading = ref(false)
const switchLoading = ref(false)
const historyLoading = ref(false)
const autoRotateLoading = ref(false)

// 分页
const currentPage = ref(1)
const pageSize = ref(20)
const historyTotal = ref(0)

// 配置表单
const configForm = reactive({
  enabled: false,
  schedule_type: 'monthly',
  schedule_day: 1,
  schedule_time: '02:00',
  auto_switch: false
})

// 计算属性
const totalRecords = computed(() => previewTables.value.reduce((sum, t) => sum + t.total, 0))
const totalNeedsMigration = computed(() => previewTables.value.reduce((sum, t) => sum + t.v1_or_legacy, 0))

const scheduleDayLabel = computed(() => {
  if (configForm.schedule_type === 'weekly') return '执行星期'
  return '执行日期'
})

const scheduleDayMin = computed(() => configForm.schedule_type === 'weekly' ? 0 : 1)
const scheduleDayMax = computed(() => configForm.schedule_type === 'weekly' ? 6 : 31)

const nextRotationDisplay = computed(() => {
  if (!configData.value?.next_rotation_at) return '未设置'
  const date = new Date(configData.value.next_rotation_at)
  return date.toLocaleString('zh-CN')
})

// 加载数据
async function loadStatus() {
  try {
    const [status, versions, stats, config] = await Promise.all([
      api.getKeyRotationStatus(),
      api.getKeyVersions(),
      api.getEncryptionStatistics(),
      api.getRotationConfig()
    ])
    
    statusData.value = status
    versionInfo.value = versions
    statistics.value = stats
    configData.value = config
    
    // 更新表单
    configForm.enabled = config.enabled
    configForm.schedule_type = config.schedule_type
    configForm.schedule_day = config.schedule_day
    configForm.schedule_time = config.schedule_time
    configForm.auto_switch = config.auto_switch
    
    // 加载预览
    await loadPreview()
  } catch (error) {
    console.error('加载状态失败:', error)
  }
}

async function loadPreview() {
  previewLoading.value = true
  try {
    const result = await api.getMigrationPreview()
    previewTables.value = result.preview_tables
  } catch (error) {
    console.error('加载预览失败:', error)
  } finally {
    previewLoading.value = false
  }
}

async function loadHistory() {
  historyLoading.value = true
  try {
    const result = await api.getRotationHistory(currentPage.value, pageSize.value)
    historyLogs.value = result.logs
    historyTotal.value = result.total
  } catch (error) {
    console.error('加载历史失败:', error)
  } finally {
    historyLoading.value = false
  }
}

// 配置变更
async function handleConfigChange() {
  try {
    const result = await api.updateRotationConfig({
      enabled: configForm.enabled,
      schedule_type: configForm.schedule_type,
      schedule_day: configForm.schedule_day,
      schedule_time: configForm.schedule_time,
      auto_switch: configForm.auto_switch
    })
    configData.value = result
    ElMessage.success('配置已保存')
  } catch (error) {
    ElMessage.error('配置保存失败')
  }
}

// 预览迁移
async function handlePreview() {
  await loadPreview()
  ElMessage.success('预览已刷新')
}

// 执行迁移
async function handleMigrate() {
  try {
    await ElMessageBox.confirm(
      `确定要执行数据迁移吗？这将把 ${totalNeedsMigration.value} 条记录从旧密钥迁移到 V2。`,
      '确认迁移',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    
    migrateLoading.value = true
    const result = await api.executeMigration()
    
    if (result.success) {
      ElMessage.success(`迁移完成！成功迁移 ${result.total_migrated} 条记录`)
    } else {
      ElMessage.warning(`迁移完成，但有 ${result.total_failed} 条记录失败`)
    }
    
    // 刷新数据
    await loadStatus()
    await loadHistory()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('迁移失败')
    }
  } finally {
    migrateLoading.value = false
  }
}

// 切换版本
async function handleSwitchVersion() {
  const currentVersion = statusData.value?.current_version || 'v1'
  const targetVersion = currentVersion === 'v1' ? 'v2' : 'v1'
  
  try {
    await ElMessageBox.confirm(
      `确定要切换到 ${targetVersion.toUpperCase()} 版本吗？切换后新数据将使用新密钥加密。`,
      '确认切换',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )
    
    switchLoading.value = true
    const result = await api.switchKeyVersion(targetVersion)
    
    ElMessage.success(result.message)
    await loadStatus()
    await loadHistory()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('切换失败')
    }
  } finally {
    switchLoading.value = false
  }
}

// 手动触发自动轮换
async function handleTriggerAutoRotation() {
  try {
    await ElMessageBox.confirm(
      '确定要手动触发自动轮换吗？这将执行数据迁移并根据配置决定是否切换版本。',
      '确认执行',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    
    autoRotateLoading.value = true
    const result = await api.triggerAutoRotation()
    
    ElMessage.success(result.message)
    await loadStatus()
    await loadHistory()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('执行失败')
    }
  } finally {
    autoRotateLoading.value = false
  }
}

// 辅助函数
function getActionType(action) {
  const map = { preview: 'info', migrate: 'warning', switch: 'success' }
  return map[action] || 'info'
}

function getActionLabel(action) {
  const map = { preview: '预览', migrate: '迁移', switch: '切换' }
  return map[action] || action
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  const date = new Date(timeStr)
  return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  loadStatus()
  loadHistory()
})
</script>

<style scoped>
.key-rotation-container {
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}

.subtitle {
  color: #909399;
  margin: 0;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  height: 100%;
}

.stat-card :deep(.el-card__body) {
  padding: 20px;
}

.stat-content {
  display: flex;
  align-items: center;
  gap: 16px;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.version-icon {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.total-icon {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

.pending-icon {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  color: white;
}

.v2-icon {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.main-content {
  display: flex;
  gap: 20px;
}

.config-card {
  height: fit-content;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.card-header span {
  display: flex;
  align-items: center;
  gap: 8px;
}

.version-status {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.version-item :deep(.el-tag) {
  display: flex;
  align-items: center;
  gap: 6px;
}

.config-form {
  margin-bottom: 20px;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.migration-preview {
  margin: 16px 0;
}

.preview-summary {
  margin-top: 12px;
  text-align: center;
  color: #606266;
  font-size: 14px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  justify-content: center;
}

.history-card {
  margin-bottom: 20px;
}

.history-pagination {
  margin-top: 16px;
  justify-content: center;
}

.next-rotation-card :deep(.el-card__body) {
  text-align: center;
}

.next-rotation-time {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin-bottom: 12px;
}

.time-icon {
  font-size: 20px;
  color: #409eff;
}
</style>
