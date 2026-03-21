<template>
  <div class="performance-page">
    <!-- 实例选择和筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-select v-model="selectedInstance" placeholder="选择实例" @change="handleInstanceChange" style="width: 100%;">
            <el-option
              v-for="inst in instances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            >
              <span style="float: left">{{ inst.name }}</span>
              <span style="float: right; color: #8492a6; font-size: 12px">
                <el-tag :color="inst.environment?.color" size="small" style="border: none">
                  {{ inst.environment?.name }}
                </el-tag>
              </span>
            </el-option>
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-select v-model="timeRange" @change="fetchData" style="width: 100%;">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近12小时" :value="12" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="fetchData" :loading="loading">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
          <el-button @click="toggleAutoRefresh">
            <el-icon><Timer /></el-icon>
            {{ autoRefresh ? '停止刷新' : '自动刷新' }}
          </el-button>
        </el-col>
      </el-row>
    </el-card>

    <!-- 实时指标卡片 -->
    <el-row :gutter="20" class="metrics-cards">
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-icon cpu">
              <el-icon :size="28"><Cpu /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">
                {{ currentMetrics.cpu_usage?.toFixed(1) || '--' }}
                <span class="metric-unit">%</span>
              </div>
              <div class="metric-label">CPU 使用率</div>
              <div class="metric-stats" v-if="statistics.cpu_usage">
                <span class="max">Max: {{ statistics.cpu_usage.max?.toFixed(1) }}%</span>
                <span class="avg">Avg: {{ statistics.cpu_usage.avg?.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <el-progress 
            :percentage="currentMetrics.cpu_usage || 0" 
            :color="getProgressColor(currentMetrics.cpu_usage)"
            :stroke-width="6"
            :show-text="false"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-icon memory">
              <el-icon :size="28"><Coin /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">
                {{ currentMetrics.memory_usage?.toFixed(1) || '--' }}
                <span class="metric-unit">%</span>
              </div>
              <div class="metric-label">内存使用率</div>
              <div class="metric-stats" v-if="statistics.memory_usage">
                <span class="max">Max: {{ statistics.memory_usage.max?.toFixed(1) }}%</span>
                <span class="avg">Avg: {{ statistics.memory_usage.avg?.toFixed(1) }}%</span>
              </div>
            </div>
          </div>
          <el-progress 
            :percentage="currentMetrics.memory_usage || 0" 
            :color="getProgressColor(currentMetrics.memory_usage)"
            :stroke-width="6"
            :show-text="false"
          />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-icon connections">
              <el-icon :size="28"><Connection /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">
                {{ currentMetrics.connections || '--' }}
              </div>
              <div class="metric-label">活跃连接数</div>
              <div class="metric-stats" v-if="statistics.connections">
                <span class="max">Max: {{ statistics.connections.max }}</span>
                <span class="avg">Avg: {{ statistics.connections.avg?.toFixed(0) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="metric-card">
          <div class="metric-content">
            <div class="metric-icon qps">
              <el-icon :size="28"><TrendCharts /></el-icon>
            </div>
            <div class="metric-info">
              <div class="metric-value">
                {{ currentMetrics.qps?.toFixed(0) || '--' }}
              </div>
              <div class="metric-label">QPS</div>
              <div class="metric-stats" v-if="statistics.qps">
                <span class="max">Max: {{ statistics.qps.max?.toFixed(0) }}</span>
                <span class="avg">Avg: {{ statistics.qps.avg?.toFixed(0) }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>CPU 使用率趋势</span>
              <el-tag size="small" :type="getMetricStatus(currentMetrics.cpu_usage)">
                {{ getMetricStatusText(currentMetrics.cpu_usage) }}
              </el-tag>
            </div>
          </template>
          <div ref="cpuChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>内存使用率趋势</span>
              <el-tag size="small" :type="getMetricStatus(currentMetrics.memory_usage)">
                {{ getMetricStatusText(currentMetrics.memory_usage) }}
              </el-tag>
            </div>
          </template>
          <div ref="memoryChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" class="charts-row">
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>连接数趋势</span>
            </div>
          </template>
          <div ref="connectionsChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never" class="chart-card">
          <template #header>
            <div class="chart-header">
              <span>QPS 趋势</span>
            </div>
          </template>
          <div ref="qpsChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 暂无数据提示 -->
    <el-empty v-if="!selectedInstance" description="请选择一个实例查看性能监控数据" />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Timer, Cpu, Coin, Connection, TrendCharts } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import request from '@/api/index'
import dayjs from 'dayjs'

// 状态
const loading = ref(false)
const autoRefresh = ref(false)
const autoRefreshTimer = ref(null)
const instances = ref([])
const selectedInstance = ref(null)
const timeRange = ref(1)
const historyData = ref([])
const currentMetrics = ref({})
const statistics = ref({})

// 图表引用
const cpuChartRef = ref(null)
const memoryChartRef = ref(null)
const connectionsChartRef = ref(null)
const qpsChartRef = ref(null)

// 图表实例
let cpuChart = null
let memoryChart = null
let connectionsChart = null
let qpsChart = null

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    instances.value = data.items || []
    if (instances.value.length > 0 && !selectedInstance.value) {
      selectedInstance.value = instances.value[0].id
      fetchData()
    }
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 获取数据
const fetchData = async () => {
  if (!selectedInstance.value) return
  
  loading.value = true
  try {
    // 并行获取历史数据和统计数据
    const [historyRes, statsRes] = await Promise.all([
      request.get(`/performance/${selectedInstance.value}/history`, { params: { hours: timeRange.value } }),
      request.get(`/performance/${selectedInstance.value}/statistics`, { params: { hours: timeRange.value } })
    ])
    
    historyData.value = Array.isArray(historyRes) ? historyRes : (historyRes.items || [])
    statistics.value = statsRes || {}
    
    // 更新当前指标
    if (historyData.value.length > 0) {
      currentMetrics.value = historyData.value[historyData.value.length - 1]
    }
    
    // 更新图表
    await nextTick()
    updateCharts()
  } catch (error) {
    console.error('获取性能数据失败:', error)
    ElMessage.error('获取性能数据失败')
  } finally {
    loading.value = false
  }
}

// 实例变更
const handleInstanceChange = () => {
  fetchData()
}

// 切换自动刷新
const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    autoRefreshTimer.value = setInterval(fetchData, 30000) // 30秒刷新一次
    ElMessage.success('已开启自动刷新（30秒）')
  } else {
    clearInterval(autoRefreshTimer.value)
    ElMessage.info('已停止自动刷新')
  }
}

// 获取进度条颜色
const getProgressColor = (value) => {
  if (value >= 80) return '#f56c6c'
  if (value >= 60) return '#e6a23c'
  return '#67c23a'
}

// 获取指标状态
const getMetricStatus = (value) => {
  if (value >= 80) return 'danger'
  if (value >= 60) return 'warning'
  return 'success'
}

// 获取指标状态文本
const getMetricStatusText = (value) => {
  if (value >= 80) return '高负载'
  if (value >= 60) return '中等负载'
  if (value > 0) return '正常'
  return '未知'
}

// 初始化图表
const initCharts = () => {
  // CPU 图表
  if (cpuChartRef.value) {
    cpuChart = echarts.init(cpuChartRef.value)
  }
  // 内存图表
  if (memoryChartRef.value) {
    memoryChart = echarts.init(memoryChartRef.value)
  }
  // 连接数图表
  if (connectionsChartRef.value) {
    connectionsChart = echarts.init(connectionsChartRef.value)
  }
  // QPS 图表
  if (qpsChartRef.value) {
    qpsChart = echarts.init(qpsChartRef.value)
  }
}

// 更新图表
const updateCharts = () => {
  const times = historyData.value.map(d => dayjs(d.collect_time).format('HH:mm'))
  
  // 通用图表配置
  const baseOption = {
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(50, 50, 50, 0.9)',
      borderColor: '#333',
      textStyle: { color: '#fff' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: times,
      axisLine: { lineStyle: { color: '#ddd' } },
      axisLabel: { color: '#666', fontSize: 11 }
    }
  }
  
  // CPU 图表
  if (cpuChart) {
    const cpuData = historyData.value.map(d => d.cpu_usage?.toFixed(2) || 0)
    cpuChart.setOption({
      ...baseOption,
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', color: '#666' },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      series: [{
        name: 'CPU使用率',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.3)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.05)' }
          ])
        },
        lineStyle: { color: '#409eff', width: 2 },
        itemStyle: { color: '#409eff' },
        data: cpuData,
        markLine: {
          silent: true,
          data: [
            { yAxis: 80, lineStyle: { color: '#f56c6c', type: 'dashed' }, label: { formatter: '告警线' } },
            { yAxis: 60, lineStyle: { color: '#e6a23c', type: 'dashed' }, label: { formatter: '警戒线' } }
          ]
        }
      }]
    })
  }
  
  // 内存图表
  if (memoryChart) {
    const memoryData = historyData.value.map(d => d.memory_usage?.toFixed(2) || 0)
    memoryChart.setOption({
      ...baseOption,
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: { formatter: '{value}%', color: '#666' },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      series: [{
        name: '内存使用率',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
            { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
          ])
        },
        lineStyle: { color: '#67c23a', width: 2 },
        itemStyle: { color: '#67c23a' },
        data: memoryData,
        markLine: {
          silent: true,
          data: [
            { yAxis: 80, lineStyle: { color: '#f56c6c', type: 'dashed' }, label: { formatter: '告警线' } },
            { yAxis: 60, lineStyle: { color: '#e6a23c', type: 'dashed' }, label: { formatter: '警戒线' } }
          ]
        }
      }]
    })
  }
  
  // 连接数图表
  if (connectionsChart) {
    const connectionsData = historyData.value.map(d => d.connections || 0)
    const maxConn = Math.max(...connectionsData, 100)
    connectionsChart.setOption({
      ...baseOption,
      yAxis: {
        type: 'value',
        min: 0,
        max: Math.ceil(maxConn * 1.2),
        axisLabel: { color: '#666' },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      series: [{
        name: '连接数',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(230, 162, 60, 0.3)' },
            { offset: 1, color: 'rgba(230, 162, 60, 0.05)' }
          ])
        },
        lineStyle: { color: '#e6a23c', width: 2 },
        itemStyle: { color: '#e6a23c' },
        data: connectionsData
      }]
    })
  }
  
  // QPS 图表
  if (qpsChart) {
    const qpsData = historyData.value.map(d => d.qps?.toFixed(2) || 0)
    const maxQps = Math.max(...qpsData.map(Number), 100)
    qpsChart.setOption({
      ...baseOption,
      yAxis: {
        type: 'value',
        min: 0,
        max: Math.ceil(maxQps * 1.2),
        axisLabel: { color: '#666' },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      series: [{
        name: 'QPS',
        type: 'line',
        smooth: true,
        symbol: 'none',
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(144, 147, 153, 0.3)' },
            { offset: 1, color: 'rgba(144, 147, 153, 0.05)' }
          ])
        },
        lineStyle: { color: '#909399', width: 2 },
        itemStyle: { color: '#909399' },
        data: qpsData
      }]
    })
  }
}

// 窗口大小变化时重绘图表
const handleResize = () => {
  cpuChart?.resize()
  memoryChart?.resize()
  connectionsChart?.resize()
  qpsChart?.resize()
}

onMounted(() => {
  fetchInstances()
  initCharts()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (autoRefreshTimer.value) {
    clearInterval(autoRefreshTimer.value)
  }
  cpuChart?.dispose()
  memoryChart?.dispose()
  connectionsChart?.dispose()
  qpsChart?.dispose()
  window.removeEventListener('resize', handleResize)
})

// 监听实例变化
watch(selectedInstance, () => {
  fetchData()
})
</script>

<style lang="scss" scoped>
.performance-page {
  .filter-card {
    margin-bottom: 20px;
  }
  
  .metrics-cards {
    margin-bottom: 20px;
    
    .metric-card {
      .metric-content {
        display: flex;
        align-items: center;
        margin-bottom: 15px;
        
        .metric-icon {
          width: 56px;
          height: 56px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-right: 15px;
          color: #fff;
          
          &.cpu { background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%); }
          &.memory { background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%); }
          &.connections { background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%); }
          &.qps { background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%); }
        }
        
        .metric-info {
          flex: 1;
          
          .metric-value {
            font-size: 28px;
            font-weight: bold;
            color: #303133;
            line-height: 1.2;
            
            .metric-unit {
              font-size: 14px;
              font-weight: normal;
              color: #909399;
              margin-left: 2px;
            }
          }
          
          .metric-label {
            font-size: 13px;
            color: #909399;
            margin-top: 4px;
          }
          
          .metric-stats {
            font-size: 11px;
            color: #c0c4cc;
            margin-top: 6px;
            
            span {
              margin-right: 10px;
              
              &.max { color: #f56c6c; }
              &.avg { color: #909399; }
            }
          }
        }
      }
    }
  }
  
  .charts-row {
    margin-bottom: 20px;
    
    .chart-card {
      .chart-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      
      .chart-container {
        height: 280px;
      }
    }
  }
}
</style>
