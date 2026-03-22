<template>
  <div class="instance-detail">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="instance-title">{{ instance?.name }}</span>
        <el-tag :type="instance?.status ? 'success' : 'danger'" size="small">
          {{ instance?.status ? '在线' : '离线' }}
        </el-tag>
      </template>
    </el-page-header>
    
    <el-tabs v-model="activeTab" class="detail-tabs">
      <!-- 基本信息 -->
      <el-tab-pane label="基本信息" name="info">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="实例名称">{{ instance?.name }}</el-descriptions-item>
          <el-descriptions-item label="地址">{{ instance?.host }}:{{ instance?.port }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ instance?.username }}</el-descriptions-item>
          <el-descriptions-item label="环境">
            <span
              v-if="instance?.environment"
              class="env-tag"
              :style="{ backgroundColor: instance.environment.color, color: '#FFFFFF' }"
            >
              {{ instance.environment.name }}
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ instance?.description || '-' }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatTime(instance?.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="最后检查">{{ formatTime(instance?.last_check_time) }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      
      <!-- 监控开关 -->
      <el-tab-pane label="监控配置" name="monitor">
        <el-card shadow="never">
          <template #header>
            <span>监控开关配置</span>
          </template>
          
          <el-table :data="monitorSwitches" style="width: 100%">
            <el-table-column prop="monitor_type" label="监控类型" width="200">
              <template #default="{ row }">
                {{ getMonitorTypeLabel(row.monitor_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="状态" width="100">
              <template #default="{ row }">
                <el-switch
                  v-model="row.enabled"
                  :disabled="!isAdmin"
                  @change="handleSwitchChange(row)"
                />
              </template>
            </el-table-column>
            <el-table-column prop="configured_at" label="配置时间" width="200">
              <template #default="{ row }">
                {{ formatTime(row.configured_at) }}
              </template>
            </el-table-column>
            <el-table-column label="配置" width="100">
              <template #default="{ row }">
                <div class="table-operations">
                  <el-button link type="primary" size="small" @click="showConfig(row)">配置</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
      
      <!-- 性能监控 -->
      <el-tab-pane label="性能监控" name="performance">
        <div class="performance-section">
          <el-row :gutter="20">
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-title">CPU使用率</div>
                <div class="metric-value">{{ currentPerformance?.cpu_usage?.toFixed(1) || '-' }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-title">内存使用率</div>
                <div class="metric-value">{{ currentPerformance?.memory_usage?.toFixed(1) || '-' }}%</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-title">连接数</div>
                <div class="metric-value">{{ currentPerformance?.connections || '-' }}</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="metric-card">
                <div class="metric-title">QPS</div>
                <div class="metric-value">{{ currentPerformance?.qps?.toFixed(0) || '-' }}</div>
              </div>
            </el-col>
          </el-row>
          
          <!-- 图表占位 -->
          <el-card shadow="never" style="margin-top: 20px;">
            <div class="chart-placeholder">
              <p>性能趋势图表（待实现ECharts图表）</p>
            </div>
          </el-card>
        </div>
      </el-tab-pane>
      
      <!-- 参数配置 -->
      <el-tab-pane label="参数配置" name="variables">
        <el-input
          v-model="variableSearch"
          placeholder="搜索参数名"
          prefix-icon="Search"
          style="margin-bottom: 20px; width: 300px;"
        />
        <el-table :data="filteredVariables" style="width: 100%" max-height="500">
          <el-table-column prop="name" label="参数名" width="300" />
          <el-table-column prop="value" label="值" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { instancesApi } from '@/api/instances'
import { monitorApi } from '@/api/monitor'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const isAdmin = computed(() => userStore.isAdmin)
const canOperate = computed(() => userStore.canOperate)

const instance = ref(null)
const activeTab = ref('info')
const monitorSwitches = ref([])
const currentPerformance = ref(null)
const variables = ref([])
const variableSearch = ref('')

const instanceId = computed(() => route.params.id)

// 过滤后的参数列表
const filteredVariables = computed(() => {
  if (!variableSearch.value) {
    return Object.entries(variables.value).map(([name, value]) => ({ name, value }))
  }
  const search = variableSearch.value.toLowerCase()
  return Object.entries(variables.value)
    .filter(([name]) => name.toLowerCase().includes(search))
    .map(([name, value]) => ({ name, value }))
})

// 获取实例详情
const fetchInstance = async () => {
  try {
    instance.value = await instancesApi.getDetail(instanceId.value)
  } catch (error) {
    console.error('获取实例详情失败:', error)
  }
}

// 获取监控开关
const fetchMonitorSwitches = async () => {
  try {
    monitorSwitches.value = await monitorApi.getInstanceSwitches(instanceId.value)
  } catch (error) {
    console.error('获取监控开关失败:', error)
  }
}

// 获取当前性能
const fetchCurrentPerformance = async () => {
  try {
    const result = await monitorApi.performance.getCurrent(instanceId.value)
    if (result.enabled && result.data) {
      currentPerformance.value = result.data
    }
  } catch (error) {
    console.error('获取性能数据失败:', error)
  }
}

// 获取参数
const fetchVariables = async () => {
  try {
    variables.value = await instancesApi.getVariables(instanceId.value)
  } catch (error) {
    console.error('获取参数失败:', error)
  }
}

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

// 处理开关变化
const handleSwitchChange = async (row) => {
  try {
    await monitorApi.updateInstanceSwitch(instanceId.value, row.monitor_type, {
      enabled: row.enabled
    })
    ElMessage.success(`${getMonitorTypeLabel(row.monitor_type)}已${row.enabled ? '启用' : '禁用'}`)
  } catch (error) {
    row.enabled = !row.enabled
  }
}

// 显示配置
const showConfig = (row) => {
  ElMessage.info('详细配置功能开发中')
}

// 返回
const goBack = () => {
  router.back()
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

onMounted(() => {
  fetchInstance()
  fetchMonitorSwitches()
  fetchCurrentPerformance()
  fetchVariables()
})
</script>

<style lang="scss" scoped>
.instance-detail {
  .instance-title {
    margin-right: 10px;
    font-size: 18px;
    font-weight: 500;
  }
  
  .detail-tabs {
    margin-top: 20px;
    
    .performance-section {
      .metric-card {
        background: #fff;
        border-radius: 8px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        
        .metric-title {
          color: #999;
          font-size: 14px;
          margin-bottom: 10px;
        }
        
        .metric-value {
          font-size: 28px;
          font-weight: bold;
          color: #333;
        }
      }
      
      .chart-placeholder {
        height: 300px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #999;
        background: #f9f9f9;
        border-radius: 8px;
      }
    }
  }
}
</style>
