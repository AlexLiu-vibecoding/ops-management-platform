<template>
  <div class="slow-query-list">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #409eff;">
            <el-icon :size="24"><Timer /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_count }}</div>
            <div class="stat-label">慢查询总数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #e6a23c;">
            <el-icon :size="24"><DataAnalysis /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.total_executions }}</div>
            <div class="stat-label">总执行次数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #f56c6c;">
            <el-icon :size="24"><Warning /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.max_time?.toFixed(2) }}s</div>
            <div class="stat-label">最大耗时</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-icon" style="background: #67c23a;">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="stat-content">
            <div class="stat-value">{{ stats.avg_time?.toFixed(2) }}s</div>
            <div class="stat-label">平均耗时</div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 实例选择和筛选 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="实例">
          <el-select v-model="selectedInstance" placeholder="选择实例" @change="fetchSlowQueries" style="width: 200px;">
            <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="耗时阈值">
          <el-input-number v-model="minTime" :min="0.1" :max="3600" :step="0.1" :precision="1" style="width: 120px;" />
          <span class="unit-label">秒</span>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-select v-model="timeRange" placeholder="时间范围" @change="fetchSlowQueries" style="width: 140px;">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchSlowQueries" :loading="loading">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="resetFilters">重置</el-button>
          <el-button type="success" @click="openFetchDialog" :disabled="!selectedInstance">
            <el-icon><Download /></el-icon>
            从 RDS 抓取
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 慢查询列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>慢查询列表</span>
          <el-tag type="info">共 {{ slowQueries.length }} 条</el-tag>
        </div>
      </template>
      
      <el-table :data="slowQueries" v-loading="loading" style="width: 100%" @row-click="showDetail">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="sql-expand">
              <div class="sql-label">SQL 语句：</div>
              <pre class="sql-content">{{ row.sql_sample || row.sql_fingerprint }}</pre>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="database_name" label="数据库" width="100" />
        <el-table-column label="SQL指纹" min-width="200">
          <template #default="{ row }">
            <div class="sql-fingerprint">{{ row.sql_fingerprint || '-' }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="query_time" label="耗时" width="80" sortable align="right">
          <template #default="{ row }">
            <el-tag :type="getQueryTimeType(row.query_time)" size="small">{{ row.query_time?.toFixed(2) }}s</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rows_examined" label="扫描行" width="80" align="right">
          <template #default="{ row }">{{ formatNumber(row.rows_examined) }}</template>
        </el-table-column>
        <el-table-column prop="rows_sent" label="返回行" width="80" align="right">
          <template #default="{ row }">{{ formatNumber(row.rows_sent) }}</template>
        </el-table-column>
        <el-table-column prop="execution_count" label="执行次数" width="80" align="center" />
        <el-table-column prop="last_seen" label="最后执行" width="160">
          <template #default="{ row }">{{ formatTime(row.last_seen) }}</template>
        </el-table-column>
        <el-table-column label="操作" min-width="80" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions :row="row" :actions="slowQueryActions" @explain="analyzeQuery" />
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchSlowQueries"
          @current-change="fetchSlowQueries"
        />
      </div>
    </el-card>
    
    <!-- EXPLAIN 分析对话框 -->
    <el-dialog v-model="explainDialog.visible" title="EXPLAIN 分析" width="90%" top="5vh" :close-on-click-modal="false">
      <div class="explain-content" v-if="explainDialog.data">
        <!-- SQL 信息 -->
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <span>SQL 信息</span>
              <el-tag :type="getQueryTimeType(explainDialog.data.query_time)">
                耗时: {{ explainDialog.data.query_time?.toFixed(2) }}s
              </el-tag>
            </div>
          </template>
          <div class="sql-info">
            <div class="info-row">
              <span class="info-label">数据库:</span>
              <span class="info-value">{{ explainDialog.data.database_name || '-' }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">执行次数:</span>
              <span class="info-value">{{ explainDialog.data.execution_count }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">扫描行数:</span>
              <span class="info-value">{{ formatNumber(explainDialog.data.rows_examined) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">返回行数:</span>
              <span class="info-value">{{ formatNumber(explainDialog.data.rows_sent) }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">锁等待:</span>
              <span class="info-value">{{ explainDialog.data.lock_time?.toFixed(3) || 0 }}s</span>
            </div>
          </div>
          <div class="sql-box">
            <pre>{{ explainDialog.data.sql_sample }}</pre>
          </div>
        </el-card>
        
        <!-- EXPLAIN 结果 -->
        <el-card shadow="never" class="explain-card" v-if="explainDialog.data.explain?.length">
          <template #header><span>执行计划</span></template>
          <el-table :data="explainDialog.data.explain" border style="width: 100%">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="select_type" label="查询类型" width="120">
              <template #default="{ row }">
                <el-tag size="small" :type="getSelectTypeTag(row.select_type)">{{ row.select_type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="table" label="表" width="120" />
            <el-table-column prop="type" label="访问类型" width="100">
              <template #default="{ row }">
                <el-tag size="small" :type="getTypeTag(row.type)">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="possible_keys" label="可能索引" min-width="150">
              <template #default="{ row }">
                <span class="index-cell">{{ row.possible_keys || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="key" label="实际索引" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.key && row.key !== 'NULL'" type="success" size="small">{{ row.key }}</el-tag>
                <el-tag v-else type="danger" size="small">无</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="rows" label="预估行数" width="100">
              <template #default="{ row }">{{ formatNumber(row.rows) }}</template>
            </el-table-column>
            <el-table-column prop="Extra" label="额外信息" min-width="200">
              <template #default="{ row }">
                <div class="extra-cell">{{ row.Extra || '-' }}</div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 错误信息 -->
        <el-alert v-if="explainDialog.data.explain?.error" :title="explainDialog.data.explain.error" type="error" :closable="false" show-icon style="margin-bottom: 20px;" />
        
        <!-- 优化建议 -->
        <el-card shadow="never" class="suggestions-card" v-if="explainDialog.data.suggestions?.length">
          <template #header>
            <div class="card-header">
              <span>基础优化建议</span>
              <el-tag size="small" type="info">规则引擎</el-tag>
            </div>
          </template>
          <div class="suggestions-list">
            <div v-for="(suggestion, idx) in explainDialog.data.suggestions" :key="idx" class="suggestion-item" :class="suggestion.type">
              <div class="suggestion-icon">
                <el-icon v-if="suggestion.type === 'warning'" :size="20"><Warning /></el-icon>
                <el-icon v-else-if="suggestion.type === 'error'" :size="20"><CircleClose /></el-icon>
                <el-icon v-else-if="suggestion.type === 'success'" :size="20"><CircleCheck /></el-icon>
                <el-icon v-else :size="20"><InfoFilled /></el-icon>
              </div>
              <div class="suggestion-content">
                <div class="suggestion-title">{{ suggestion.title }}</div>
                <div class="suggestion-desc">{{ suggestion.description }}</div>
                <div class="suggestion-action">{{ suggestion.action }}</div>
              </div>
            </div>
          </div>
        </el-card>
      </div>
      
      <template #footer>
        <el-button @click="explainDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="copySQL">复制 SQL</el-button>
      </template>
    </el-dialog>
    
    <!-- 从 RDS 抓取慢查询对话框 -->
    <el-dialog v-model="fetchDialog.visible" title="从 AWS RDS 抓取慢查询" width="90%" top="5vh" :close-on-click-modal="false">
      <el-alert type="info" :closable="false" style="margin-bottom: 20px;">
        <template #title>
          <div style="display: flex; align-items: center; gap: 10px;">
            <el-icon><InfoFilled /></el-icon>
            <span>通过 MySQL performance_schema 抓取慢查询，无需访问 slow.log 文件</span>
          </div>
        </template>
      </el-alert>
      
      <!-- 抓取配置 -->
      <el-card shadow="never" class="config-card">
        <template #header><span>抓取配置</span></template>
        <el-form :model="fetchDialog.config" label-width="120px">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item label="最小执行时间">
                <el-input-number v-model="fetchDialog.config.minExecTime" :min="0.1" :max="3600" :step="0.1" :precision="1" style="width: 100%;">
                  <template #suffix>秒</template>
                </el-input-number>
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="返回条数限制">
                <el-input-number v-model="fetchDialog.config.limit" :min="10" :max="500" :step="10" style="width: 100%;" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="过滤数据库">
                <el-select v-model="fetchDialog.config.database" placeholder="全部数据库" clearable style="width: 100%;">
                  <el-option v-for="db in fetchDialog.databases" :key="db" :label="db" :value="db" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form>
      </el-card>
      
      <!-- 抓取结果 -->
      <el-card shadow="never" class="result-card" v-if="fetchDialog.results.length > 0">
        <template #header>
          <div class="card-header">
            <span>抓取结果 ({{ fetchDialog.results.length }} 条)</span>
          </div>
        </template>
        <el-table :data="fetchDialog.results" style="width: 100%" max-height="400">
          <el-table-column prop="schema_name" label="数据库" width="100" />
          <el-table-column label="SQL 摘要" min-width="300">
            <template #default="{ row }">
              <div class="sql-digest">{{ row.digest_text || row.sample_query }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="exec_count" label="执行次数" width="90" sortable />
          <el-table-column label="平均耗时" width="100" sortable>
            <template #default="{ row }">
              <el-tag :type="getQueryTimeType(row.avg_exec_time_sec || row.avg_latency_sec)">
                {{ (row.avg_exec_time_sec || row.avg_latency_sec)?.toFixed(2) }}s
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rows_examined" label="扫描行数" width="100">
            <template #default="{ row }">{{ formatNumber(row.rows_examined) }}</template>
          </el-table-column>
          <el-table-column prop="last_seen" label="最后执行" width="140">
            <template #default="{ row }">{{ formatTime(row.last_seen) }}</template>
          </el-table-column>
        </el-table>
      </el-card>
      
      <template #footer>
        <el-button @click="fetchDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="fetchFromPerformanceSchema" :loading="fetchDialog.fetching">开始抓取</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, DataAnalysis, Warning, TrendCharts, CircleClose, CircleCheck, InfoFilled, Download, Search } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'
import TableActions from '@/components/TableActions.vue'

const emit = defineEmits(['analyze'])

// 操作列配置
const slowQueryActions = [
  { key: 'explain', label: 'EXPLAIN', event: 'explain', primary: true }
]

const loading = ref(false)
const instances = ref([])
const selectedInstance = ref(null)
const minTime = ref(1.0)
const timeRange = ref(24)
const slowQueries = ref([])

// 筛选表单
const filters = reactive({
  instance: null,
  minTime: 1.0,
  timeRange: 24
})

const stats = ref({
  total_count: 0,
  total_executions: 0,
  max_time: 0,
  avg_time: 0
})

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const explainDialog = reactive({
  visible: false,
  loading: false,
  data: null
})

// 从 RDS 抓取慢查询对话框
const fetchDialog = reactive({
  visible: false,
  fetching: false,
  databases: [],
  results: [],
  config: {
    minExecTime: 1.0,
    limit: 100,
    database: null
  }
})

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    instances.value = (data.items || []).filter(inst => inst.db_type !== 'redis')
    if (instances.value.length > 0 && !selectedInstance.value) {
      selectedInstance.value = instances.value[0].id
      await fetchSlowQueries()
    }
  } catch (error) {
    console.error('获取实例列表失败:', error)
    ElMessage.error('获取实例列表失败，请刷新页面重试')
  }
}

// 获取慢查询列表
const fetchSlowQueries = async () => {
  if (!selectedInstance.value) {
    ElMessage.warning('请先选择实例')
    return
  }
  
  loading.value = true
  try {
    const params = {
      limit: pagination.limit
    }
    if (minTime.value) {
      params.min_time = minTime.value
    }
    
    const [queriesData, statsData] = await Promise.all([
      request.get(`/slow-query/${selectedInstance.value}`, { params }),
      request.get(`/slow-query/${selectedInstance.value}/statistics`, { params: { hours: timeRange.value } })
    ])
    
    slowQueries.value = queriesData
    stats.value = statsData
    pagination.total = statsData.total_count
  } catch (error) {
    console.error('获取慢查询失败:', error)
    ElMessage.error('获取慢查询数据失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  minTime.value = 1.0
  timeRange.value = 24
  fetchSlowQueries()
}

// 分析慢查询
const analyzeQuery = async (row) => {
  explainDialog.visible = true
  explainDialog.loading = true
  explainDialog.data = null
  
  try {
    const data = await request.get(`/slow-query/${selectedInstance.value}/analysis/${row.id}`)
    explainDialog.data = data
    emit('analyze', row)
  } catch (error) {
    ElMessage.error('获取EXPLAIN分析失败')
    console.error(error)
  } finally {
    explainDialog.loading = false
  }
}

// 显示详情
const showDetail = (row) => {
  // 展开行显示SQL
}

// 复制SQL
const copySQL = async () => {
  if (explainDialog.data?.sql_sample) {
    try {
      await navigator.clipboard.writeText(explainDialog.data.sql_sample)
      ElMessage.success('SQL已复制到剪贴板')
    } catch (e) {
      ElMessage.error('复制失败')
    }
  }
}

// 打开抓取对话框
const openFetchDialog = async () => {
  if (!selectedInstance.value) {
    ElMessage.warning('请先选择实例')
    return
  }
  
  fetchDialog.visible = true
  fetchDialog.results = []
  
  // 获取数据库列表
  try {
    const data = await request.get(`/slow-query/${selectedInstance.value}/databases`)
    fetchDialog.databases = data.databases || []
  } catch (error) {
    console.error('获取数据库列表失败:', error)
    fetchDialog.databases = []
  }
}

// 从 performance_schema 抓取慢查询
const fetchFromPerformanceSchema = async () => {
  fetchDialog.fetching = true
  fetchDialog.results = []
  
  try {
    const params = {
      limit: fetchDialog.config.limit,
      min_exec_time: fetchDialog.config.minExecTime
    }
    if (fetchDialog.config.database) {
      params.database_name = fetchDialog.config.database
    }
    
    const data = await request.get(`/slow-query/${selectedInstance.value}/fetch-slow-queries`, { params })
    fetchDialog.results = data.items || []
    
    ElMessage.success(`成功抓取 ${fetchDialog.results.length} 条慢查询`)
    
    // 同步到本地
    if (fetchDialog.results.length > 0) {
      await syncAllToLocal()
    }
  } catch (error) {
    console.error('抓取慢查询失败:', error)
    ElMessage.error(error.response?.data?.detail || '抓取慢查询失败')
  } finally {
    fetchDialog.fetching = false
  }
}

// 同步所有抓取结果到本地
const syncAllToLocal = async () => {
  try {
    const params = {
      limit: fetchDialog.config.limit,
      min_exec_time: fetchDialog.config.minExecTime
    }
    if (fetchDialog.config.database) {
      params.database_name = fetchDialog.config.database
    }
    
    const data = await request.post(`/slow-query/${selectedInstance.value}/sync-slow-queries`, null, { params })
    ElMessage.success(`同步完成: 新增 ${data.saved_count} 条, 更新 ${data.updated_count} 条`)
    
    // 刷新本地慢查询列表
    await fetchSlowQueries()
  } catch (error) {
    console.error('同步慢查询失败:', error)
    ElMessage.error(error.response?.data?.detail || '同步慢查询失败')
  }
}

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K'
  return num.toLocaleString()
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('MM-DD HH:mm') : '-'
}

// 获取查询耗时标签类型
const getQueryTimeType = (time) => {
  if (!time) return 'info'
  if (time >= 10) return 'danger'
  if (time >= 3) return 'warning'
  return 'success'
}

// 获取 select_type 标签类型
const getSelectTypeTag = (type) => {
  const types = {
    'SIMPLE': 'success',
    'PRIMARY': '',
    'DERIVED': 'warning',
    'SUBQUERY': 'info',
    'UNION': 'warning'
  }
  return types[type] || 'info'
}

// 获取 type 标签类型
const getTypeTag = (type) => {
  const types = {
    'system': 'success',
    'const': 'success',
    'eq_ref': 'success',
    'ref': 'success',
    'ref_or_null': 'warning',
    'range': 'warning',
    'index': 'warning',
    'ALL': 'danger'
  }
  return types[type] || 'info'
}

// 暴露方法供父组件调用
defineExpose({
  fetchData: fetchSlowQueries
})

onMounted(() => {
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.slow-query-list {
  .stats-row {
    margin-bottom: 20px;
  }
  
  .stat-card {
    :deep(.el-card__body) {
      display: flex;
      align-items: center;
      padding: 20px;
    }
    
    .stat-icon {
      width: 50px;
      height: 50px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      margin-right: 15px;
    }
    
    .stat-content {
      .stat-value {
        font-size: 24px;
        font-weight: bold;
        color: #303133;
      }
      .stat-label {
        font-size: 13px;
        color: #909399;
        margin-top: 5px;
      }
    }
  }
  
  .filter-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .sql-fingerprint {
      font-family: monospace;
      font-size: 12px;
      color: #606266;
    }
    
    .sql-expand {
      padding: 10px 20px;
      background: #f5f7fa;
      
      .sql-label {
        font-weight: bold;
        margin-bottom: 8px;
        color: #606266;
      }
      
      .sql-content {
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        margin: 0;
        color: #303133;
      }
    }
  }
  
  .pagination {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
  }
  
  .explain-content {
    .info-card {
      margin-bottom: 20px;
      
      .sql-info {
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        margin-bottom: 15px;
        
        .info-row {
          .info-label {
            color: #909399;
            margin-right: 8px;
          }
          .info-value {
            font-weight: 500;
          }
        }
      }
      
      .sql-box {
        background: #f5f7fa;
        padding: 15px;
        border-radius: 4px;
        
        pre {
          margin: 0;
          font-family: monospace;
          font-size: 13px;
          white-space: pre-wrap;
          word-break: break-all;
        }
      }
    }
    
    .explain-card {
      margin-bottom: 20px;
      
      .index-cell {
        font-family: monospace;
        font-size: 12px;
      }
      
      .extra-cell {
        font-family: monospace;
        font-size: 12px;
        color: #606266;
      }
    }
    
    .suggestions-card {
      .suggestions-list {
        .suggestion-item {
          display: flex;
          padding: 15px;
          margin-bottom: 10px;
          border-radius: 8px;
          border-left: 4px solid;
          
          &.warning {
            background: #fdf6ec;
            border-color: #e6a23c;
            .suggestion-icon { color: #e6a23c; }
          }
          
          &.error {
            background: #fef0f0;
            border-color: #f56c6c;
            .suggestion-icon { color: #f56c6c; }
          }
          
          &.success {
            background: #f0f9eb;
            border-color: #67c23a;
            .suggestion-icon { color: #67c23a; }
          }
          
          &.info {
            background: #f4f4f5;
            border-color: #909399;
            .suggestion-icon { color: #909399; }
          }
          
          .suggestion-icon {
            margin-right: 15px;
            flex-shrink: 0;
          }
          
          .suggestion-content {
            flex: 1;
            
            .suggestion-title {
              font-weight: bold;
              font-size: 14px;
              color: #303133;
              margin-bottom: 5px;
            }
            
            .suggestion-desc {
              font-size: 13px;
              color: #606266;
              margin-bottom: 5px;
            }
            
            .suggestion-action {
              font-size: 12px;
              color: #409eff;
            }
          }
        }
      }
    }
  }
}

// 抓取对话框样式
.config-card {
  margin-bottom: 20px;
}

.result-card {
  .sql-digest {
    font-family: monospace;
    font-size: 12px;
    color: #606266;
    word-break: break-all;
  }
}
</style>
