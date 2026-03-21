<template>
  <div class="monitor-settings">
    <el-tabs v-model="activeTab" class="settings-tabs">
      <!-- 慢查询监控配置 -->
      <el-tab-pane label="慢查询监控" name="slowQuery">
        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">
              <span>慢查询监控配置</span>
              <el-switch
                v-model="slowQueryConfig.enabled"
                active-text="启用"
                inactive-text="禁用"
                :disabled="!isAdmin"
              />
            </div>
          </template>
          
          <el-form :model="slowQueryConfig" label-width="160px" :disabled="!slowQueryConfig.enabled || !isAdmin">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="慢查询阈值">
                  <el-input-number
                    v-model="slowQueryConfig.threshold"
                    :min="0.1"
                    :max="3600"
                    :step="0.1"
                    :precision="1"
                  />
                  <span class="unit">秒</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="采集间隔">
                  <el-input-number
                    v-model="slowQueryConfig.collect_interval"
                    :min="60"
                    :max="3600"
                    :step="60"
                  />
                  <span class="unit">秒</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="慢查询日志路径">
              <el-input
                v-model="slowQueryConfig.log_path"
                placeholder="/var/log/mysql/slow.log"
              />
            </el-form-item>
            
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="分析工具">
                  <el-radio-group v-model="slowQueryConfig.analysis_tool">
                    <el-radio label="built-in">内置分析</el-radio>
                    <el-radio label="pt-query-digest">pt-query-digest</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="自动分析">
                  <el-switch v-model="slowQueryConfig.auto_analyze" />
                  <span class="hint">自动分析慢查询日志并生成报告</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="数据保留天数">
                  <el-input-number
                    v-model="slowQueryConfig.retention_days"
                    :min="1"
                    :max="365"
                  />
                  <span class="unit">天</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Top N 数量">
                  <el-input-number
                    v-model="slowQueryConfig.top_n"
                    :min="1"
                    :max="100"
                  />
                  <span class="hint">展示最耗时的N条慢查询</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item v-if="isAdmin">
              <el-button type="primary" @click="saveSlowQueryConfig" :loading="saving">
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 慢查询统计 -->
        <el-card shadow="never" class="stats-card">
          <template #header>
            <span>慢查询统计 (最近24小时)</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in slowQueryStatsItems" :key="item.label">
              <div class="stat-item">
                <div class="stat-value">{{ item.value }}</div>
                <div class="stat-label">{{ item.label }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>
      
      <!-- 高CPU SQL监控配置 -->
      <el-tab-pane label="高CPU SQL监控" name="highCpu">
        <el-card shadow="never" class="settings-card">
          <template #header>
            <div class="card-header">
              <span>高CPU SQL监控配置</span>
              <el-switch
                v-model="highCpuConfig.enabled"
                active-text="启用"
                inactive-text="禁用"
                :disabled="!isAdmin"
              />
            </div>
          </template>
          
          <el-form :model="highCpuConfig" label-width="160px" :disabled="!highCpuConfig.enabled || !isAdmin">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="CPU告警阈值">
                  <el-input-number
                    v-model="highCpuConfig.cpu_threshold"
                    :min="0"
                    :max="100"
                    :step="5"
                  />
                  <span class="unit">%</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="内存告警阈值">
                  <el-input-number
                    v-model="highCpuConfig.memory_threshold"
                    :min="0"
                    :max="100"
                    :step="5"
                  />
                  <span class="unit">%</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="采集间隔">
                  <el-input-number
                    v-model="highCpuConfig.collect_interval"
                    :min="1"
                    :max="60"
                  />
                  <span class="unit">秒</span>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="告警冷却时间">
                  <el-input-number
                    v-model="highCpuConfig.alert_cooldown"
                    :min="60"
                    :max="3600"
                    :step="60"
                  />
                  <span class="unit">秒</span>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="实时追踪">
              <el-switch v-model="highCpuConfig.track_realtime" />
              <span class="hint">实时追踪高CPU使用的SQL语句</span>
            </el-form-item>
            
            <el-form-item label="自动Kill">
              <el-switch v-model="highCpuConfig.auto_kill" />
              <el-tag type="danger" size="small" style="margin-left: 10px">危险操作</el-tag>
              <span class="hint">达到阈值时自动Kill高CPU进程</span>
            </el-form-item>
            
            <template v-if="highCpuConfig.auto_kill">
              <el-row :gutter="20">
                <el-col :span="12">
                  <el-form-item label="自动Kill阈值">
                    <el-input-number
                      v-model="highCpuConfig.auto_kill_threshold"
                      :min="0"
                      :max="100"
                      :step="5"
                    />
                    <span class="unit">%</span>
                    <div class="hint">CPU使用率超过此值时自动Kill</div>
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="最长执行时间">
                    <el-input-number
                      v-model="highCpuConfig.max_kill_time"
                      :min="10"
                      :max="3600"
                      :step="10"
                    />
                    <span class="unit">秒</span>
                    <div class="hint">执行时间超过此值的查询将被Kill</div>
                  </el-form-item>
                </el-col>
              </el-row>
            </template>
            
            <el-form-item v-if="isAdmin">
              <el-button type="primary" @click="saveHighCpuConfig" :loading="saving">
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
        
        <!-- 高CPU统计 -->
        <el-card shadow="never" class="stats-card">
          <template #header>
            <span>高CPU SQL统计 (最近24小时)</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="item in highCpuStatsItems" :key="item.label">
              <div class="stat-item">
                <div class="stat-value">{{ item.value }}</div>
                <div class="stat-label">{{ item.label }}</div>
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>
      
      <!-- 告警规则配置 -->
      <el-tab-pane label="告警规则" name="alertRules">
        <el-card shadow="never" class="alert-rules-card">
          <template #header>
            <div class="card-header">
              <span>告警规则配置</span>
              <el-button type="primary" size="small" @click="saveAlertRulesDetail" :loading="saving" v-if="isAdmin">
                保存全部规则
              </el-button>
            </div>
          </template>
          
          <el-table :data="alertRulesDetail" style="width: 100%">
            <el-table-column prop="name" label="规则名称" width="180" />
            <el-table-column prop="metric_type" label="指标类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ getMetricTypeLabel(row.metric_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="operator" label="操作符" width="80" />
            <el-table-column prop="threshold" label="阈值" width="120">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.threshold"
                  size="small"
                  :min="0"
                  :max="1000"
                  :step="5"
                  style="width: 100px"
                  :disabled="!isAdmin"
                />
              </template>
            </el-table-column>
            <el-table-column prop="severity" label="严重级别" width="120">
              <template #default="{ row }">
                <el-select v-model="row.severity" size="small" style="width: 100px" :disabled="!isAdmin">
                  <el-option label="提示" value="info" />
                  <el-option label="警告" value="warning" />
                  <el-option label="严重" value="critical" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column prop="cooldown" label="冷却时间" width="120">
              <template #default="{ row }">
                <el-input-number
                  v-model="row.cooldown"
                  size="small"
                  :min="60"
                  :max="3600"
                  :step="60"
                  style="width: 100px"
                  :disabled="!isAdmin"
                />
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="状态" width="80">
              <template #default="{ row }">
                <el-switch v-model="row.enabled" :disabled="!isAdmin" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <!-- 全局开关配置 -->
      <el-tab-pane label="全局开关" name="globalSwitches">
        <el-card shadow="never" class="settings-card">
          <template #header>
            <span>全局监控开关</span>
          </template>
          <el-row :gutter="20">
            <el-col :span="6" v-for="(enabled, type) in globalSwitches" :key="type">
              <div class="switch-item">
                <span class="switch-label">{{ getMonitorTypeLabel(type) }}</span>
                <el-switch
                  v-model="globalSwitches[type]"
                  :disabled="!isAdmin"
                  @change="handleGlobalSwitchChange(type, $event)"
                />
              </div>
            </el-col>
          </el-row>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const activeTab = ref('slowQuery')
const saving = ref(false)

// 全局开关
const globalSwitches = reactive({
  slow_query: true,
  cpu_sql: true,
  performance: true,
  inspection: true
})

// 慢查询配置
const slowQueryConfig = reactive({
  enabled: true,
  threshold: 1.0,
  collect_interval: 300,
  log_path: '',
  analysis_tool: 'built-in',
  auto_analyze: true,
  retention_days: 30,
  top_n: 10
})

// 高CPU配置
const highCpuConfig = reactive({
  enabled: true,
  cpu_threshold: 80.0,
  memory_threshold: 80.0,
  collect_interval: 10,
  track_realtime: true,
  auto_kill: false,
  auto_kill_threshold: 95.0,
  max_kill_time: 300,
  alert_cooldown: 300
})

// 告警规则
const alertRulesDetail = ref([])

// 统计数据
const slowQueryStats = ref({
  total_count: 0,
  total_executions: 0,
  max_time: 0,
  avg_time: 0
})

const highCpuStats = ref({
  max_cpu: 0,
  avg_cpu: 0,
  max_memory: 0,
  avg_memory: 0
})

// 统计数据展示项
const slowQueryStatsItems = computed(() => [
  { label: '慢查询总数', value: slowQueryStats.value.total_count },
  { label: '总执行次数', value: slowQueryStats.value.total_executions },
  { label: '最大耗时', value: slowQueryStats.value.max_time?.toFixed(2) + 's' },
  { label: '平均耗时', value: slowQueryStats.value.avg_time?.toFixed(2) + 's' }
])

const highCpuStatsItems = computed(() => [
  { label: '最高CPU使用率', value: highCpuStats.value.max_cpu?.toFixed(1) + '%' },
  { label: '平均CPU使用率', value: highCpuStats.value.avg_cpu?.toFixed(1) + '%' },
  { label: '最高内存使用率', value: highCpuStats.value.max_memory?.toFixed(1) + '%' },
  { label: '平均内存使用率', value: highCpuStats.value.avg_memory?.toFixed(1) + '%' }
])

// 获取监控类型标签
const getMonitorTypeLabel = (type) => {
  const labels = {
    slow_query: '慢查询监控',
    cpu_sql: '高CPU SQL监控',
    performance: '性能监控',
    inspection: '实例巡检'
  }
  return labels[type] || type
}

// 获取指标类型标签
const getMetricTypeLabel = (type) => {
  const labels = {
    cpu: 'CPU',
    memory: '内存',
    disk: '磁盘',
    connections: '连接数',
    qps: 'QPS',
    slow_query: '慢查询'
  }
  return labels[type] || type
}

// 获取全局开关
const fetchGlobalSwitches = async () => {
  try {
    const data = await monitorApi.getGlobalSwitches()
    Object.assign(globalSwitches, data)
  } catch (error) {
    console.error('获取全局开关失败:', error)
  }
}

// 处理全局开关变化
const handleGlobalSwitchChange = async (type, enabled) => {
  try {
    await monitorApi.updateGlobalSwitch({
      monitor_type: type,
      enabled: enabled
    })
    ElMessage.success(`${getMonitorTypeLabel(type)}已${enabled ? '启用' : '禁用'}`)
  } catch (error) {
    globalSwitches[type] = !enabled
  }
}

// 加载慢查询配置
const loadSlowQueryConfig = async () => {
  try {
    const res = await monitorApi.getSlowQueryConfig()
    Object.assign(slowQueryConfig, res)
  } catch (error) {
    console.error('加载慢查询配置失败:', error)
  }
}

// 加载高CPU配置
const loadHighCpuConfig = async () => {
  try {
    const res = await monitorApi.getHighCpuConfig()
    Object.assign(highCpuConfig, res)
  } catch (error) {
    console.error('加载高CPU配置失败:', error)
  }
}

// 加载告警规则
const loadAlertRulesDetail = async () => {
  try {
    const res = await monitorApi.getAlertRulesDetail()
    alertRulesDetail.value = res
  } catch (error) {
    console.error('加载告警规则失败:', error)
  }
}

// 加载统计数据
const loadStatistics = async () => {
  try {
    const [slowRes, highCpuRes] = await Promise.all([
      monitorApi.getSlowQueryStatistics(),
      monitorApi.getHighCpuStatistics()
    ])
    slowQueryStats.value = slowRes
    highCpuStats.value = highCpuRes
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 保存慢查询配置
const saveSlowQueryConfig = async () => {
  saving.value = true
  try {
    await monitorApi.updateSlowQueryConfig(slowQueryConfig)
    ElMessage.success('慢查询监控配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存高CPU配置
const saveHighCpuConfig = async () => {
  saving.value = true
  try {
    await monitorApi.updateHighCpuConfig(highCpuConfig)
    ElMessage.success('高CPU SQL监控配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

// 保存告警规则
const saveAlertRulesDetail = async () => {
  saving.value = true
  try {
    await monitorApi.updateAlertRulesDetail(alertRulesDetail.value)
    ElMessage.success('告警规则保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchGlobalSwitches()
  loadSlowQueryConfig()
  loadHighCpuConfig()
  loadAlertRulesDetail()
  loadStatistics()
})
</script>

<style lang="scss" scoped>
.monitor-settings {
  .settings-tabs {
    background: white;
    padding: 20px;
    border-radius: 8px;
  }

  .settings-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .unit {
      margin-left: 10px;
      color: #909399;
    }
    
    .hint {
      margin-left: 10px;
      color: #909399;
      font-size: 12px;
    }
  }
  
  .stats-card {
    margin-top: 20px;
    
    .stat-item {
      text-align: center;
      padding: 20px;
      background: #f5f7fa;
      border-radius: 8px;
    }
    
    .stat-value {
      font-size: 28px;
      font-weight: bold;
      color: #409eff;
    }
    
    .stat-label {
      margin-top: 8px;
      color: #909399;
      font-size: 14px;
    }
  }
  
  .switch-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    background: #f9f9f9;
    border-radius: 8px;
    margin-bottom: 10px;
    
    .switch-label {
      font-weight: 500;
    }
  }
  
  .alert-rules-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
