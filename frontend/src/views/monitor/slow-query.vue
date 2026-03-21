<template>
  <div class="slow-query-page">
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
      <el-row :gutter="20" align="middle">
        <el-col :span="6">
          <el-select v-model="selectedInstance" placeholder="选择实例" @change="fetchSlowQueries" style="width: 100%;">
            <el-option
              v-for="inst in instances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-input-number v-model="minTime" :min="0.1" :max="3600" :step="0.1" :precision="1" placeholder="最小耗时" style="width: 100%;" />
        </el-col>
        <el-col :span="4">
          <el-select v-model="timeRange" placeholder="时间范围" @change="fetchSlowQueries" style="width: 100%;">
            <el-option label="最近1小时" :value="1" />
            <el-option label="最近6小时" :value="6" />
            <el-option label="最近24小时" :value="24" />
            <el-option label="最近7天" :value="168" />
          </el-select>
        </el-col>
        <el-col :span="4">
          <el-button type="primary" @click="fetchSlowQueries" :loading="loading">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-col>
      </el-row>
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
        <el-table-column prop="database_name" label="数据库" width="120" />
        <el-table-column label="SQL指纹" min-width="300">
          <template #default="{ row }">
            <div class="sql-fingerprint">{{ truncateSQL(row.sql_fingerprint) }}</div>
          </template>
        </el-table-column>
        <el-table-column prop="query_time" label="耗时" width="100" sortable>
          <template #default="{ row }">
            <el-tag :type="getQueryTimeType(row.query_time)">{{ row.query_time?.toFixed(2) }}s</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="rows_examined" label="扫描行数" width="100">
          <template #default="{ row }">
            {{ formatNumber(row.rows_examined) }}
          </template>
        </el-table-column>
        <el-table-column prop="rows_sent" label="返回行数" width="100">
          <template #default="{ row }">
            {{ formatNumber(row.rows_sent) }}
          </template>
        </el-table-column>
        <el-table-column prop="execution_count" label="执行次数" width="90" />
        <el-table-column prop="last_seen" label="最后执行" width="160">
          <template #default="{ row }">
            {{ formatTime(row.last_seen) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click.stop="analyzeQuery(row)">EXPLAIN</el-button>
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
          <template #header>
            <span>执行计划</span>
          </template>
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
              <template #default="{ row }">
                {{ formatNumber(row.rows) }}
              </template>
            </el-table-column>
            <el-table-column prop="Extra" label="额外信息" min-width="200">
              <template #default="{ row }">
                <div class="extra-cell">{{ row.Extra || '-' }}</div>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 错误信息 -->
        <el-alert
          v-if="explainDialog.data.explain?.error"
          :title="explainDialog.data.explain.error"
          type="error"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />
        
        <!-- 优化建议 -->
        <el-card shadow="never" class="suggestions-card" v-if="explainDialog.data.suggestions?.length">
          <template #header>
            <div class="card-header">
              <span>基础优化建议</span>
              <el-tag size="small" type="info">规则引擎</el-tag>
            </div>
          </template>
          <div class="suggestions-list">
            <div
              v-for="(suggestion, idx) in explainDialog.data.suggestions"
              :key="idx"
              class="suggestion-item"
              :class="suggestion.type"
            >
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
        
        <!-- AI 智能分析 -->
        <el-card shadow="never" class="llm-card" v-if="explainDialog.data.llm_analysis?.success">
          <template #header>
            <div class="card-header">
              <span>AI 智能分析</span>
              <el-tag size="small" type="success">大模型</el-tag>
            </div>
          </template>
          
          <div class="llm-content" v-if="explainDialog.data.llm_analysis.analysis">
            <!-- 问题总结 -->
            <div class="llm-section" v-if="explainDialog.data.llm_analysis.analysis.summary">
              <div class="llm-section-title">问题总结</div>
              <div class="llm-summary">{{ explainDialog.data.llm_analysis.analysis.summary }}</div>
            </div>
            
            <!-- 发现的问题 -->
            <div class="llm-section" v-if="explainDialog.data.llm_analysis.analysis.issues?.length">
              <div class="llm-section-title">发现的问题</div>
              <div class="llm-issues">
                <div 
                  v-for="(issue, idx) in explainDialog.data.llm_analysis.analysis.issues" 
                  :key="idx"
                  class="llm-issue-item"
                  :class="issue.severity"
                >
                  <div class="issue-header">
                    <el-tag :type="getSeverityType(issue.severity)" size="small">{{ issue.type }}</el-tag>
                    <span class="issue-location" v-if="issue.location">{{ issue.location }}</span>
                  </div>
                  <div class="issue-desc">{{ issue.description }}</div>
                </div>
              </div>
            </div>
            
            <!-- 优化建议 -->
            <div class="llm-section" v-if="explainDialog.data.llm_analysis.analysis.suggestions?.length">
              <div class="llm-section-title">优化建议</div>
              <div class="llm-suggestions">
                <div 
                  v-for="(suggestion, idx) in explainDialog.data.llm_analysis.analysis.suggestions" 
                  :key="idx"
                  class="llm-suggestion-item"
                >
                  <div class="suggestion-header">
                    <el-tag :type="getPriorityType(suggestion.priority)" size="small">{{ suggestion.priority }}</el-tag>
                    <span class="suggestion-type">{{ suggestion.type }}</span>
                  </div>
                  <div class="suggestion-desc">{{ suggestion.description }}</div>
                  <div class="suggestion-action" v-if="suggestion.action">
                    <strong>操作步骤：</strong>{{ suggestion.action }}
                  </div>
                  <div class="suggestion-effect" v-if="suggestion.expected_improvement">
                    <strong>预期效果：</strong>{{ suggestion.expected_improvement }}
                  </div>
                </div>
              </div>
            </div>
            
            <!-- 优化后的SQL -->
            <div class="llm-section" v-if="explainDialog.data.llm_analysis.analysis.optimized_sql">
              <div class="llm-section-title">优化后的 SQL</div>
              <div class="llm-sql-box">
                <pre>{{ explainDialog.data.llm_analysis.analysis.optimized_sql }}</pre>
                <el-button size="small" type="primary" link @click="copyOptimizedSQL">复制</el-button>
              </div>
            </div>
            
            <!-- 建议创建的索引 -->
            <div class="llm-section" v-if="explainDialog.data.llm_analysis.analysis.create_index_sql">
              <div class="llm-section-title">建议创建索引</div>
              <div class="llm-sql-box">
                <pre>{{ explainDialog.data.llm_analysis.analysis.create_index_sql }}</pre>
                <el-button size="small" type="primary" link @click="copyIndexSQL">复制</el-button>
              </div>
            </div>
          </div>
        </el-card>
        
        <!-- LLM 分析失败 -->
        <el-alert
          v-else-if="explainDialog.data.llm_analysis && !explainDialog.data.llm_analysis.success"
          :title="`AI 分析失败: ${explainDialog.data.llm_analysis.error}`"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 20px;"
        />
      </div>
      
      <template #footer>
        <el-button @click="explainDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="copySQL">复制 SQL</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Timer, DataAnalysis, Warning, TrendCharts, CircleClose, CircleCheck, InfoFilled } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

const loading = ref(false)
const instances = ref([])
const selectedInstance = ref(null)
const minTime = ref(1.0)
const timeRange = ref(24)
const slowQueries = ref([])
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

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    instances.value = data.items || []
    if (instances.value.length > 0 && !selectedInstance.value) {
      selectedInstance.value = instances.value[0].id
      fetchSlowQueries()
    }
  } catch (error) {
    console.error('获取实例列表失败:', error)
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

// 截断SQL显示
const truncateSQL = (sql) => {
  if (!sql) return '-'
  return sql.length > 80 ? sql.substring(0, 80) + '...' : sql
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

// 获取严重级别标签类型
const getSeverityType = (severity) => {
  const types = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return types[severity] || 'info'
}

// 获取优先级标签类型
const getPriorityType = (priority) => {
  const types = {
    'high': 'danger',
    'medium': 'warning',
    'low': 'info'
  }
  return types[priority] || 'info'
}

// 复制优化后的SQL
const copyOptimizedSQL = async () => {
  const sql = explainDialog.data?.llm_analysis?.analysis?.optimized_sql
  if (sql) {
    try {
      await navigator.clipboard.writeText(sql)
      ElMessage.success('优化SQL已复制到剪贴板')
    } catch (e) {
      ElMessage.error('复制失败')
    }
  }
}

// 复制索引创建SQL
const copyIndexSQL = async () => {
  const sql = explainDialog.data?.llm_analysis?.analysis?.create_index_sql
  if (sql) {
    try {
      await navigator.clipboard.writeText(sql)
      ElMessage.success('索引SQL已复制到剪贴板')
    } catch (e) {
      ElMessage.error('复制失败')
    }
  }
}

onMounted(() => {
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.slow-query-page {
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
    
    .llm-card {
      margin-top: 20px;
      border: 1px solid #e1f3d8;
      background: linear-gradient(135deg, #f6ffed 0%, #ffffff 100%);
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      
      .llm-content {
        .llm-section {
          margin-bottom: 20px;
          
          &:last-child {
            margin-bottom: 0;
          }
          
          .llm-section-title {
            font-weight: bold;
            font-size: 14px;
            color: #303133;
            margin-bottom: 10px;
            padding-left: 10px;
            border-left: 3px solid #67c23a;
          }
          
          .llm-summary {
            background: #f5f7fa;
            padding: 12px 15px;
            border-radius: 6px;
            font-size: 14px;
            color: #303133;
            line-height: 1.6;
          }
        }
        
        .llm-issues {
          .llm-issue-item {
            padding: 12px 15px;
            margin-bottom: 10px;
            border-radius: 6px;
            background: #fafafa;
            
            &.high {
              border-left: 3px solid #f56c6c;
            }
            
            &.medium {
              border-left: 3px solid #e6a23c;
            }
            
            &.low {
              border-left: 3px solid #909399;
            }
            
            .issue-header {
              display: flex;
              align-items: center;
              gap: 10px;
              margin-bottom: 8px;
              
              .issue-location {
                color: #909399;
                font-size: 12px;
              }
            }
            
            .issue-desc {
              font-size: 13px;
              color: #606266;
            }
          }
        }
        
        .llm-suggestions {
          .llm-suggestion-item {
            padding: 15px;
            margin-bottom: 12px;
            border-radius: 8px;
            background: #fff;
            border: 1px solid #e4e7ed;
            
            .suggestion-header {
              display: flex;
              align-items: center;
              gap: 10px;
              margin-bottom: 10px;
              
              .suggestion-type {
                font-weight: 500;
                color: #303133;
              }
            }
            
            .suggestion-desc {
              font-size: 14px;
              color: #303133;
              margin-bottom: 8px;
            }
            
            .suggestion-action {
              font-size: 13px;
              color: #606266;
              margin-bottom: 5px;
              background: #f5f7fa;
              padding: 8px 12px;
              border-radius: 4px;
            }
            
            .suggestion-effect {
              font-size: 13px;
              color: #67c23a;
            }
          }
        }
        
        .llm-sql-box {
          background: #1e1e1e;
          padding: 15px;
          border-radius: 6px;
          position: relative;
          
          pre {
            margin: 0;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 13px;
            color: #d4d4d4;
            white-space: pre-wrap;
            word-break: break-all;
          }
          
          .el-button {
            position: absolute;
            top: 10px;
            right: 10px;
          }
        }
      }
    }
  }
}
</style>
