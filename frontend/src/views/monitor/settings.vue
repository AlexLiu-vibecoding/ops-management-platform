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
                    <el-radio value="built-in">内置分析</el-radio>
                    <el-radio value="pt-query-digest">pt-query-digest</el-radio>
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
        <!-- 搜索栏 -->
        <el-card shadow="never" class="filter-card">
          <el-form :inline="true" :model="alertQueryParams" @submit.prevent="loadAlertRules">
            <el-form-item label="规则名称">
              <el-input v-model="alertQueryParams.search" placeholder="请输入规则名称" clearable @keyup.enter="loadAlertRules" />
            </el-form-item>
            <el-form-item label="规则类型">
              <el-select v-model="alertQueryParams.rule_type" placeholder="全部" clearable style="width: 120px">
                <el-option v-for="item in ruleTypes" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="alertQueryParams.is_enabled" placeholder="全部" clearable style="width: 100px">
                <el-option label="启用" :value="true" />
                <el-option label="禁用" :value="false" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadAlertRules">搜索</el-button>
              <el-button @click="resetAlertQuery">重置</el-button>
              <el-button type="success" @click="handleAddRule" v-if="isAdmin">
                <el-icon><Plus /></el-icon>
                新增规则
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 规则列表 -->
        <el-card shadow="never">
          <el-table v-loading="alertLoading" :data="alertRules" stripe>
            <el-table-column prop="name" label="规则名称" min-width="150" />
            <el-table-column prop="rule_type_label" label="规则类型" width="120" />
            <el-table-column label="条件" min-width="150">
              <template #default="{ row }">
                {{ row.metric_name }} {{ row.operator_label }} {{ row.threshold }} (持续{{ row.duration }}s)
              </template>
            </el-table-column>
            <el-table-column label="告警级别" width="100">
              <template #default="{ row }">
                <el-tag :color="row.severity_color" class="text-white">
                  {{ row.severity_label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="静默期" width="100">
              <template #default="{ row }">
                {{ row.silence_duration }}s
              </template>
            </el-table-column>
            <el-table-column prop="is_enabled" label="状态" min-width="80">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="触发次数" width="100">
              <template #default="{ row }">
                {{ row.trigger_count || 0 }}
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="120" fixed="right" align="center">
              <template #default="{ row }">
                <TableActions :row="row" :actions="ruleActions" @edit="handleEditRule" @toggle="handleToggleRule" @delete="handleDeleteRule" />
              </template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="alertQueryParams.page"
              v-model:page-size="alertQueryParams.limit"
              :total="alertTotal"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="loadAlertRules"
              @current-change="loadAlertRules"
            />
          </div>
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

    <!-- 新增/编辑告警规则对话框 -->
    <el-dialog v-model="ruleDialog.visible" :title="ruleDialog.isEdit ? '编辑规则' : '新增规则'" width="700px" @close="resetRuleForm">
      <el-form ref="ruleFormRef" :model="ruleForm" :rules="ruleFormRules" label-width="120px">
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="ruleForm.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ruleForm.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="ruleForm.rule_type" placeholder="请选择规则类型" style="width: 100%">
            <el-option v-for="item in ruleTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="实例范围" prop="instance_scope">
          <el-radio-group v-model="ruleForm.instance_scope">
            <el-radio value="all">全部实例</el-radio>
            <el-radio value="selected">指定实例</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="ruleForm.instance_scope === 'selected'" label="选择实例">
          <el-select v-model="ruleForm.instance_ids" multiple placeholder="请选择实例" style="width: 100%">
            <el-option v-for="inst in instanceList" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="指标名称" prop="metric_name">
              <el-input v-model="ruleForm.metric_name" placeholder="如: cpu_usage" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="运算符" prop="operator">
              <el-select v-model="ruleForm.operator" placeholder="运算符">
                <el-option v-for="item in operators" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="阈值" prop="threshold">
              <el-input-number v-model="ruleForm.threshold" :precision="2" :min="0" style="width: 100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="持续时间" prop="duration">
              <el-input-number v-model="ruleForm.duration" :min="0" style="width: 100%" />
              <span class="unit">秒</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="聚合方式" prop="aggregation">
              <el-select v-model="ruleForm.aggregation" placeholder="聚合方式" style="width: 100%">
                <el-option v-for="item in aggregations" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="告警级别" prop="severity">
              <el-select v-model="ruleForm.severity" placeholder="告警级别" style="width: 100%">
                <el-option v-for="item in severities" :key="item.value" :label="item.label" :value="item.value">
                  <span :style="{ color: item.color }">{{ item.label }}</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="静默时长" prop="silence_duration">
              <el-input-number v-model="ruleForm.silence_duration" :min="0" style="width: 100%" />
              <span class="unit">秒</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="通知配置">
          <el-checkbox v-model="ruleForm.notify_enabled">启用通知</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="ruleDialog.submitting" @click="handleSubmitRule">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { monitorApi } from '@/api/monitor'
import { alertRulesApi } from '@/api/inspection'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/api/index'
import TableActions from '@/components/TableActions.vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const activeTab = ref('slowQuery')
const saving = ref(false)

// ========== 慢查询配置 ==========
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

const slowQueryStats = ref({
  total_count: 0,
  total_executions: 0,
  max_time: 0,
  avg_time: 0
})

const slowQueryStatsItems = computed(() => [
  { label: '慢查询总数', value: slowQueryStats.value.total_count },
  { label: '总执行次数', value: slowQueryStats.value.total_executions },
  { label: '最大耗时', value: slowQueryStats.value.max_time?.toFixed(2) + 's' },
  { label: '平均耗时', value: slowQueryStats.value.avg_time?.toFixed(2) + 's' }
])

// ========== 高CPU配置 ==========
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

const highCpuStats = ref({
  max_cpu: 0,
  avg_cpu: 0,
  max_memory: 0,
  avg_memory: 0
})

const highCpuStatsItems = computed(() => [
  { label: '最高CPU使用率', value: highCpuStats.value.max_cpu?.toFixed(1) + '%' },
  { label: '平均CPU使用率', value: highCpuStats.value.avg_cpu?.toFixed(1) + '%' },
  { label: '最高内存使用率', value: highCpuStats.value.max_memory?.toFixed(1) + '%' },
  { label: '平均内存使用率', value: highCpuStats.value.avg_memory?.toFixed(1) + '%' }
])

// ========== 全局开关 ==========
const globalSwitches = reactive({
  slow_query: true,
  cpu_sql: true,
  performance: true,
  inspection: true,
  ai_analysis: false
})

// ========== 告警规则 ==========
const alertLoading = ref(false)
const alertRules = ref([])
const alertTotal = ref(0)
const instanceList = ref([])

// 下拉选项
const ruleTypes = ref([])
const operators = ref([])
const aggregations = ref([])
const severities = ref([])

// 查询参数
const alertQueryParams = reactive({
  search: '',
  rule_type: '',
  is_enabled: undefined,
  page: 1,
  limit: 20
})

// 操作列配置
const ruleActions = computed(() => [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { 
    key: 'toggle', 
    label: (row) => row.is_enabled ? '禁用' : '启用',
    event: 'toggle',
    primary: false,
    visible: () => isAdmin.value
  },
  { key: 'delete', label: '删除', event: 'delete', danger: true, primary: false, visible: () => isAdmin.value }
])

// 规则表单
const ruleFormRef = ref()
const ruleDialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false
})

const ruleForm = reactive({
  id: 0,
  name: '',
  description: '',
  rule_type: '',
  instance_scope: 'all',
  instance_ids: [],
  metric_name: '',
  operator: '>',
  threshold: 0,
  duration: 60,
  aggregation: 'avg',
  severity: 'warning',
  silence_duration: 300,
  notify_enabled: true,
  is_enabled: true
})

const ruleFormRules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  metric_name: [{ required: true, message: '请输入指标名称', trigger: 'blur' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }],
  severity: [{ required: true, message: '请选择告警级别', trigger: 'change' }]
}

// ========== 方法 ==========

// 获取监控类型标签
const getMonitorTypeLabel = (type) => {
  const labels = {
    slow_query: '慢查询监控',
    cpu_sql: '高CPU SQL监控',
    performance: '性能监控',
    inspection: '实例巡检',
    ai_analysis: 'AI 智能分析'
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

// ========== 告警规则方法 ==========

// 加载告警规则
async function loadAlertRules() {
  alertLoading.value = true
  try {
    const data = await alertRulesApi.list(alertQueryParams)
    alertRules.value = data.items || []
    alertTotal.value = data.total || 0
  } catch (error) {
    console.error('加载告警规则失败:', error)
  } finally {
    alertLoading.value = false
  }
}

// 加载下拉选项
async function loadRuleOptions() {
  try {
    const [typesRes, opsRes, aggRes, sevRes] = await Promise.all([
      alertRulesApi.getTypes(),
      alertRulesApi.getOperators(),
      alertRulesApi.getAggregations(),
      alertRulesApi.getSeverities()
    ])
    ruleTypes.value = typesRes || []
    operators.value = opsRes || []
    aggregations.value = aggRes || []
    severities.value = sevRes || []
  } catch (error) {
    console.error('加载选项失败:', error)
  }
}

// 加载实例列表
async function loadInstances() {
  try {
    const data = await request.get('/rdb-instances', { params: { limit: 1000 } })
    instanceList.value = data.items || []
  } catch (error) {
    console.error('加载实例失败:', error)
  }
}

// 重置查询
function resetAlertQuery() {
  alertQueryParams.search = ''
  alertQueryParams.rule_type = ''
  alertQueryParams.is_enabled = undefined
  alertQueryParams.page = 1
  loadAlertRules()
}

// 新增规则
function handleAddRule() {
  resetRuleForm()
  ruleDialog.isEdit = false
  ruleDialog.visible = true
}

// 编辑规则
async function handleEditRule(row) {
  resetRuleForm()
  try {
    const data = await alertRulesApi.get(row.id)
    Object.assign(ruleForm, {
      id: data.id,
      name: data.name,
      description: data.description || '',
      rule_type: data.rule_type,
      instance_scope: data.instance_scope || 'all',
      instance_ids: data.instance_ids || [],
      metric_name: data.metric_name || '',
      operator: data.operator,
      threshold: data.threshold,
      duration: data.duration,
      aggregation: data.aggregation,
      severity: data.severity,
      silence_duration: data.silence_duration,
      notify_enabled: data.notify_enabled,
      is_enabled: data.is_enabled
    })
    ruleDialog.isEdit = true
    ruleDialog.visible = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 删除规则
async function handleDeleteRule(row) {
  try {
    await ElMessageBox.confirm('确定要删除该规则吗？', '警告', { type: 'warning' })
    await alertRulesApi.delete(row.id)
    ElMessage.success('删除成功')
    loadAlertRules()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 启用/禁用规则
async function handleToggleRule(row) {
  try {
    await alertRulesApi.toggle(row.id)
    ElMessage.success('操作成功')
    loadAlertRules()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 提交规则
async function handleSubmitRule() {
  const valid = await ruleFormRef.value?.validate()
  if (!valid) return

  ruleDialog.submitting = true
  try {
    if (ruleForm.id) {
      await alertRulesApi.update(ruleForm.id, ruleForm)
      ElMessage.success('更新成功')
    } else {
      await alertRulesApi.create(ruleForm)
      ElMessage.success('创建成功')
    }
    ruleDialog.visible = false
    loadAlertRules()
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    ruleDialog.submitting = false
  }
}

// 重置规则表单
function resetRuleForm() {
  ruleForm.id = 0
  ruleForm.name = ''
  ruleForm.description = ''
  ruleForm.rule_type = ''
  ruleForm.instance_scope = 'all'
  ruleForm.instance_ids = []
  ruleForm.metric_name = ''
  ruleForm.operator = '>'
  ruleForm.threshold = 0
  ruleForm.duration = 60
  ruleForm.aggregation = 'avg'
  ruleForm.severity = 'warning'
  ruleForm.silence_duration = 300
  ruleForm.notify_enabled = true
  ruleForm.is_enabled = true
  ruleFormRef.value?.resetFields()
}

// 监听Tab切换，懒加载告警规则数据
watch(activeTab, (newVal) => {
  if (newVal === 'alertRules' && alertRules.value.length === 0) {
    loadAlertRules()
    loadRuleOptions()
    loadInstances()
  }
})

onMounted(() => {
  fetchGlobalSwitches()
  loadSlowQueryConfig()
  loadHighCpuConfig()
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
  
  .filter-card {
    margin-bottom: 16px;
  }
  
  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 16px;
  }
  
  .text-white {
    color: #fff;
  }
}
</style>
