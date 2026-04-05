<template>
  <div class="sql-performance-page">
    <el-card class="header-card">
      <template #header>
        <div class="card-header">
          <span>📊 SQL 性能对比与优化效果量化</span>
          <el-button type="primary" @click="showHistoryDialog = true">
            历史对比记录
          </el-button>
        </div>
      </template>
      <el-alert
        title="功能说明"
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #default>
          执行优化前后的 SQL，自动采集性能指标（耗时、扫描行数、CPU/IO 占用），生成可视化对比报告
        </template>
      </el-alert>

      <el-row :gutter="20">
        <el-col :span="12">
          <div class="sql-section">
            <div class="section-header">
              <span class="label">优化前（Original）</span>
              <el-button type="primary" size="small" @click="executeOriginal" :loading="executingOriginal">
                执行并采集
              </el-button>
            </div>
            <el-input
              v-model="originalSQL"
              type="textarea"
              :rows="10"
              placeholder="输入优化前的 SQL 语句..."
              class="sql-editor"
            />
            <div v-if="originalResult" class="result-section">
              <div class="result-item">
                <span class="label">执行时间：</span>
                <span class="value">{{ originalResult.execution_time_ms?.toFixed(2) }} ms</span>
              </div>
              <div class="result-item">
                <span class="label">扫描行数：</span>
                <span class="value">{{ originalResult.rows_scanned?.toLocaleString() }} 行</span>
              </div>
              <div class="result-item">
                <span class="label">CPU 时间：</span>
                <span class="value">{{ originalResult.cpu_time_ms?.toFixed(2) }} ms</span>
              </div>
              <div class="result-item">
                <span class="label">IO 时间：</span>
                <span class="value">{{ originalResult.io_time_ms?.toFixed(2) }} ms</span>
              </div>
            </div>
          </div>
        </el-col>

        <el-col :span="12">
          <div class="sql-section">
            <div class="section-header">
              <span class="label">优化后（Optimized）</span>
              <el-button type="success" size="small" @click="executeOptimized" :loading="executingOptimized">
                执行并采集
              </el-button>
            </div>
            <el-input
              v-model="optimizedSQL"
              type="textarea"
              :rows="10"
              placeholder="输入优化后的 SQL 语句..."
              class="sql-editor"
            />
            <div v-if="optimizedResult" class="result-section">
              <div class="result-item">
                <span class="label">执行时间：</span>
                <span class="value">{{ optimizedResult.execution_time_ms?.toFixed(2) }} ms</span>
              </div>
              <div class="result-item">
                <span class="label">扫描行数：</span>
                <span class="value">{{ optimizedResult.rows_scanned?.toLocaleString() }} 行</span>
              </div>
              <div class="result-item">
                <span class="label">CPU 时间：</span>
                <span class="value">{{ optimizedResult.cpu_time_ms?.toFixed(2) }} ms</span>
              </div>
              <div class="result-item">
                <span class="label">IO 时间：</span>
                <span class="value">{{ optimizedResult.io_time_ms?.toFixed(2) }} ms</span>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <div class="action-bar">
        <el-select v-model="selectedInstance" placeholder="选择数据库实例" style="width: 300px">
          <el-option
            v-for="instance in instances"
            :key="instance.id"
            :label="`${instance.name} (${instance.host})`"
            :value="instance.id"
          />
        </el-select>
        <el-button
          type="primary"
          size="large"
          @click="comparePerformance"
          :disabled="!originalResult || !optimizedResult"
          :loading="comparing"
        >
          🚀 生成对比报告
        </el-button>
      </div>
    </el-card>

    <el-card v-if="comparison" class="comparison-card">
      <template #header>
        <div class="card-header">
          <span>📈 对比报告</span>
          <div class="header-actions">
            <el-button @click="exportReport('html')">导出 HTML</el-button>
            <el-button @click="exportReport('pdf')">导出 PDF</el-button>
          </div>
        </div>
      </template>

      <div class="summary-section">
        <div class="summary-card" :class="getSummaryClass(comparison.overall_improvement)">
          <div class="summary-icon">{{ getSummaryEmoji(comparison.overall_improvement) }}</div>
          <div class="summary-content">
            <div class="summary-title">综合改善</div>
            <div class="summary-value">{{ comparison.overall_improvement?.toFixed(2) }}%</div>
            <div class="summary-desc">{{ getSummaryDescription(comparison.overall_improvement) }}</div>
          </div>
        </div>
      </div>

      <div class="metrics-grid">
        <div class="metric-card" v-if="comparison.execution_time_improvement !== null">
          <div class="metric-icon">⏱️</div>
          <div class="metric-content">
            <div class="metric-label">执行时间</div>
            <div class="metric-value" :class="getImprovementClass(comparison.execution_time_improvement)">
              {{ comparison.execution_time_improvement > 0 ? '↓' : '↑' }}
              {{ Math.abs(comparison.execution_time_improvement).toFixed(2) }}%
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="comparison.rows_scanned_improvement !== null">
          <div class="metric-icon">🔍</div>
          <div class="metric-content">
            <div class="metric-label">扫描行数</div>
            <div class="metric-value" :class="getImprovementClass(comparison.rows_scanned_improvement)">
              {{ comparison.rows_scanned_improvement > 0 ? '↓' : '↑' }}
              {{ Math.abs(comparison.rows_scanned_improvement).toFixed(2) }}%
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="comparison.cpu_time_improvement !== null">
          <div class="metric-icon">💻</div>
          <div class="metric-content">
            <div class="metric-label">CPU 时间</div>
            <div class="metric-value" :class="getImprovementClass(comparison.cpu_time_improvement)">
              {{ comparison.cpu_time_improvement > 0 ? '↓' : '↑' }}
              {{ Math.abs(comparison.cpu_time_improvement).toFixed(2) }}%
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="comparison.io_time_improvement !== null">
          <div class="metric-icon">💾</div>
          <div class="metric-content">
            <div class="metric-label">IO 时间</div>
            <div class="metric-value" :class="getImprovementClass(comparison.io_time_improvement)">
              {{ comparison.io_time_improvement > 0 ? '↓' : '↑' }}
              {{ Math.abs(comparison.io_time_improvement).toFixed(2) }}%
            </div>
          </div>
        </div>
      </div>

      <div class="charts-section">
        <div class="chart-container">
          <div ref="barChart" class="chart"></div>
        </div>
        <div class="chart-container">
          <div ref="radarChart" class="chart"></div>
        </div>
      </div>

      <div class="analysis-section">
        <h3>📝 详细分析</h3>
        <div class="analysis-content">{{ comparison.analysis }}</div>
      </div>

      <div class="recommendations-section" v-if="comparison.recommendations?.length">
        <h3>💡 优化建议</h3>
        <div
          v-for="(rec, index) in comparison.recommendations"
          :key="index"
          class="recommendation-item"
          :class="rec.type"
        >
          <div class="rec-category">{{ rec.category }}</div>
          <div class="rec-suggestion">{{ rec.suggestion }}</div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="showHistoryDialog" title="历史对比记录" width="80%">
      <el-table :data="history" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="综合改善" width="120">
          <template #default="{ row }">
            <el-tag :type="getImprovementTagType(row.overall_improvement)">
              {{ row.overall_improvement?.toFixed(2) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="analysis" label="分析摘要" show-overflow-tooltip />
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="loadComparison(row.id)">查看</el-button>
            <el-button size="small" type="danger" @click="deleteComparison(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <el-dialog v-model="showReportDialog" title="性能报告" width="90%" fullscreen>
      <iframe v-if="reportHtml" :srcdoc="reportHtml" style="width: 100%; height: 80vh; border: none" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/index'
import * as echarts from 'echarts'

const originalSQL = ref('')
const optimizedSQL = ref('')
const selectedInstance = ref(null)
const instances = ref([])

const originalResult = ref(null)
const optimizedResult = ref(null)
const comparison = ref(null)

const executingOriginal = ref(false)
const executingOptimized = ref(false)
const comparing = ref(false)

const showHistoryDialog = ref(false)
const showReportDialog = ref(false)
const history = ref([])
const reportHtml = ref('')

const barChart = ref(null)
const radarChart = ref(null)

onMounted(async () => {
  await loadInstances()
  await loadHistory()
})

async function loadInstances() {
  try {
    const result = await request.get('/rdb-instances?status=true&limit=100')
    instances.value = result.items || []
  } catch (error) {
    ElMessage.error('加载实例失败')
  }
}

async function executeOriginal() {
  if (!selectedInstance.value) {
    ElMessage.warning('请先选择数据库实例')
    return
  }
  if (!originalSQL.value.trim()) {
    ElMessage.warning('请输入优化前的 SQL')
    return
  }

  executingOriginal.value = true
  try {
    originalResult.value = await request.post('/sql-performance/execute', {
      instance_id: selectedInstance.value,
      sql_text: originalSQL.value,
      version: 'original',
      version_description: '优化前版本'
    })
    ElMessage.success('执行成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '执行失败')
  } finally {
    executingOriginal.value = false
  }
}

async function executeOptimized() {
  if (!selectedInstance.value) {
    ElMessage.warning('请先选择数据库实例')
    return
  }
  if (!optimizedSQL.value.trim()) {
    ElMessage.warning('请输入优化后的 SQL')
    return
  }

  executingOptimized.value = true
  try {
    optimizedResult.value = await request.post('/sql-performance/execute', {
      instance_id: selectedInstance.value,
      sql_text: optimizedSQL.value,
      version: 'optimized',
      version_description: '优化后版本'
    })
    ElMessage.success('执行成功')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '执行失败')
  } finally {
    executingOptimized.value = false
  }
}

async function comparePerformance() {
  if (!originalResult.value || !optimizedResult.value) {
    ElMessage.warning('请先执行两个版本的 SQL')
    return
  }

  comparing.value = true
  try {
    comparison.value = await request.post('/sql-performance/compare', {
      source_id: originalResult.value.id,
      target_id: optimizedResult.value.id
    })

    await nextTick()
    renderCharts()

    await loadHistory()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '对比失败')
  } finally {
    comparing.value = false
  }
}

function renderCharts() {
  if (!comparison.value?.report_data) return

  const reportData = comparison.value.report_data

  // 柱状图
  if (reportData.charts?.bar && barChart.value) {
    const barData = reportData.charts.bar
    const chart = echarts.init(barChart.value)
    chart.setOption({
      title: { text: '性能指标对比', left: 'center' },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: barData.series.map(s => s.name), top: 10 },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: { type: 'category', data: barData.categories },
      yAxis: { type: 'value', name: '数值' },
      series: barData.series.map(s => ({
        name: s.name,
        type: 'bar',
        data: s.data,
        barWidth: '40%',
        itemStyle: {
          color: s.name === '优化前' ? '#ff6b6b' : '#51cf66'
        }
      }))
    })
  }

  // 雷达图
  if (reportData.charts?.radar && radarChart.value) {
    const radarData = reportData.charts.radar
    const chart = echarts.init(radarChart.value)
    chart.setOption({
      title: { text: '综合性能评估', left: 'center' },
      legend: { data: radarData.series.map(s => s.name), top: 10 },
      radar: {
        indicator: radarData.indicators,
        center: ['50%', '55%'],
        radius: '70%'
      },
      series: [{
        type: 'radar',
        data: radarData.series.map(s => ({
          value: s.data,
          name: s.name,
          areaStyle: { opacity: 0.3 }
        }))
      }]
    })
  }
}

async function exportReport(format) {
  if (!comparison.value) return

  try {
    const result = await request.get(`/sql-performance/comparisons/${comparison.value.id}/report?format=${format}`)
    
    if (format === 'html') {
      reportHtml.value = result.report
      showReportDialog.value = true
    } else {
      // PDF 需要下载
      const blob = new Blob([atob(result.report)], { type: 'application/pdf' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `sql-performance-report-${comparison.value.id}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    }
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

async function loadHistory() {
  try {
    history.value = await request.get('/sql-performance/comparisons')
  } catch (error) {
    ElMessage.error('加载历史记录失败')
  }
}

async function loadComparison(id) {
  try {
    comparison.value = await request.get(`/sql-performance/comparisons/${id}`)
    await nextTick()
    renderCharts()
    showHistoryDialog.value = false
  } catch (error) {
    ElMessage.error('加载对比记录失败')
  }
}

async function deleteComparison(id) {
  try {
    await request.delete(`/sql-performance/comparisons/${id}`)
    ElMessage.success('删除成功')
    await loadHistory()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

function getSummaryClass(improvement) {
  if (improvement > 20) return 'excellent'
  if (improvement > 10) return 'good'
  if (improvement > 0) return 'fair'
  return 'poor'
}

function getSummaryEmoji(improvement) {
  if (improvement > 20) return '🎉'
  if (improvement > 10) return '👍'
  if (improvement > 0) return '✅'
  return '⚠️'
}

function getSummaryDescription(improvement) {
  if (improvement > 20) return '优化效果显著，建议在生产环境应用'
  if (improvement > 10) return '优化效果明显，可以继续优化或应用'
  if (improvement > 0) return '有一定改善，建议继续优化'
  return '优化未带来性能提升，建议检查优化方案'
}

function getImprovementClass(improvement) {
  return improvement > 0 ? 'positive' : 'negative'
}

function getImprovementTagType(improvement) {
  if (improvement > 20) return 'success'
  if (improvement > 10) return 'primary'
  if (improvement > 0) return 'info'
  return 'warning'
}

function formatDate(date) {
  return new Date(date).toLocaleString('zh-CN')
}
</script>

<style scoped>
.sql-performance-page {
  padding: 20px;
}

.header-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sql-section {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 15px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.section-header .label {
  font-size: 16px;
  font-weight: bold;
}

.sql-editor {
  margin-bottom: 15px;
}

.result-section {
  background: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  margin-bottom: 5px;
}

.result-item .label {
  color: #666;
}

.result-item .value {
  font-weight: bold;
  color: #333;
}

.action-bar {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 20px;
}

.comparison-card {
  margin-bottom: 20px;
}

.summary-section {
  margin-bottom: 30px;
}

.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 20px;
}

.summary-card.excellent {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.summary-card.good {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
}

.summary-card.fair {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.summary-card.poor {
  background: linear-gradient(135deg, #4b6cb7 0%, #182848 100%);
}

.summary-icon {
  font-size: 48px;
}

.summary-title {
  font-size: 16px;
  opacity: 0.9;
}

.summary-value {
  font-size: 48px;
  font-weight: bold;
  margin: 10px 0;
}

.summary-desc {
  font-size: 14px;
  opacity: 0.8;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.metric-card {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 15px;
  border-left: 4px solid #409eff;
}

.metric-icon {
  font-size: 32px;
}

.metric-label {
  font-size: 14px;
  color: #666;
  margin-bottom: 5px;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
}

.metric-value.positive {
  color: #67c23a;
}

.metric-value.negative {
  color: #f56c6c;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
  gap: 30px;
  margin-bottom: 30px;
}

.chart-container {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
}

.chart {
  width: 100%;
  height: 400px;
}

.analysis-section {
  margin-bottom: 30px;
}

.analysis-section h3 {
  margin-bottom: 15px;
  color: #333;
}

.analysis-content {
  background: #f9f9f9;
  padding: 20px;
  border-radius: 8px;
  white-space: pre-wrap;
  line-height: 1.8;
  color: #555;
}

.recommendations-section h3 {
  margin-bottom: 15px;
  color: #333;
}

.recommendation-item {
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 4px;
  border-left: 4px solid #409eff;
  background: #f9f9f9;
}

.recommendation-item.success {
  border-left-color: #67c23a;
  background: #f0f9ff;
}

.recommendation-item.warning {
  border-left-color: #e6a23c;
  background: #fdf6ec;
}

.recommendation-item.info {
  border-left-color: #909399;
  background: #f4f4f5;
}

.rec-category {
  font-weight: bold;
  color: #333;
  margin-bottom: 5px;
}

.rec-suggestion {
  color: #666;
}

.header-actions {
  display: flex;
  gap: 10px;
}
</style>
