<template>
  <div class="analysis-history">
    <!-- 筛选条件 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="实例">
          <el-select v-model="filters.instance_id" placeholder="全部实例" clearable @change="fetchData" style="width: 200px;">
            <el-option
              v-for="inst in instances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="分析类型">
          <el-select v-model="filters.analysis_type" placeholder="全部" clearable @change="fetchData" style="width: 140px;">
            <el-option label="规则引擎" value="rule" />
            <el-option label="LLM 分析" value="llm" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.date_range"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            style="width: 260px;"
            @change="fetchData"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchData" :loading="loading">
            <el-icon><Search /></el-icon>
            查询
          </el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 历史列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="history" v-loading="loading" style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="history-expand">
              <!-- 分析内容 -->
              <div class="section" v-if="row.analysis_content">
                <div class="section-title">分析结果</div>
                <div class="analysis-content" v-html="formatMarkdown(row.analysis_content)"></div>
              </div>
              
              <!-- 优化建议 -->
              <div class="section" v-if="row.suggestions?.length">
                <div class="section-title">优化建议</div>
                <el-table :data="row.suggestions" size="small" border>
                  <el-table-column prop="type" label="类型" width="100">
                    <template #default="{ row: s }">
                      <el-tag :type="getSuggestionType(s.type)" size="small">{{ s.type }}</el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="description" label="描述" min-width="200" />
                  <el-table-column prop="reason" label="原因" min-width="200" />
                  <el-table-column prop="expected_improvement" label="预期提升" width="100" />
                </el-table>
              </div>
              
              <!-- SQL 样例 -->
              <div class="section" v-if="row.sql_sample">
                <div class="section-title">SQL 样例</div>
                <pre class="sql-sample">{{ row.sql_sample }}</pre>
              </div>
              
              <!-- 执行计划 -->
              <div class="section" v-if="row.explain_result?.length">
                <div class="section-title">执行计划</div>
                <el-table :data="row.explain_result" size="small" border>
                  <el-table-column prop="id" label="ID" width="60" />
                  <el-table-column prop="select_type" label="查询类型" width="120" />
                  <el-table-column prop="table" label="表" width="120" />
                  <el-table-column prop="type" label="访问类型" width="100" />
                  <el-table-column prop="key" label="索引" width="120" />
                  <el-table-column prop="rows" label="行数" width="100" />
                  <el-table-column prop="Extra" label="额外信息" min-width="200" />
                </el-table>
              </div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="实例" width="120">
          <template #default="{ row }">
            {{ row.instance_name || getInstanceName(row.instance_id) }}
          </template>
        </el-table-column>
        
        <el-table-column prop="database_name" label="数据库" width="100" />
        
        <el-table-column label="SQL 指纹" min-width="200">
          <template #default="{ row }">
            <div class="sql-fingerprint">{{ truncateSQL(row.sql_fingerprint, 60) }}</div>
          </template>
        </el-table-column>
        
        <el-table-column label="分析类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.analysis_type === 'llm' ? 'primary' : 'info'" size="small">
              {{ row.analysis_type === 'llm' ? 'LLM' : '规则' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="问题数量" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.issues_count > 0 ? 'warning' : 'success'" size="small">
              {{ row.issues_count || 0 }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="建议数量" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.suggestions_count > 0 ? 'primary' : 'info'" size="small">
              {{ row.suggestions_count || 0 }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="analyzed_by" label="分析者" width="100" />
        
        <el-table-column prop="created_at" label="分析时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" link @click="viewDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog 
      v-model="detailDialog.visible" 
      title="分析详情" 
      width="90%" 
      top="5vh"
      :close-on-click-modal="false"
    >
      <div class="detail-content" v-if="detailDialog.data">
        <!-- 基本信息 -->
        <el-card shadow="never" class="info-card">
          <template #header>
            <div class="card-header">
              <span>基本信息</span>
              <div class="tags">
                <el-tag :type="detailDialog.data.analysis_type === 'llm' ? 'primary' : 'info'" size="small">
                  {{ detailDialog.data.analysis_type === 'llm' ? 'LLM 分析' : '规则引擎分析' }}
                </el-tag>
              </div>
            </div>
          </template>
          <el-descriptions :column="4" border size="small">
            <el-descriptions-item label="实例">{{ detailDialog.data.instance_name }}</el-descriptions-item>
            <el-descriptions-item label="数据库">{{ detailDialog.data.database_name }}</el-descriptions-item>
            <el-descriptions-item label="分析时间">{{ formatTime(detailDialog.data.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="分析者">{{ detailDialog.data.analyzed_by || '系统' }}</el-descriptions-item>
          </el-descriptions>
          
          <div class="sql-section" v-if="detailDialog.data.sql_sample">
            <div class="section-label">SQL 语句</div>
            <pre class="sql-content">{{ detailDialog.data.sql_sample }}</pre>
          </div>
        </el-card>
        
        <!-- 分析内容 -->
        <el-card shadow="never" class="analysis-card" v-if="detailDialog.data.analysis_content">
          <template #header>
            <span>分析结果</span>
          </template>
          <div class="analysis-content" v-html="formatMarkdown(detailDialog.data.analysis_content)"></div>
        </el-card>
        
        <!-- 问题列表 -->
        <el-card shadow="never" class="issues-card" v-if="detailDialog.data.issues?.length">
          <template #header>
            <div class="card-header">
              <span>发现的问题</span>
              <el-tag type="warning">{{ detailDialog.data.issues.length }} 个</el-tag>
            </div>
          </template>
          <div class="issues-list">
            <div 
              v-for="(issue, idx) in detailDialog.data.issues" 
              :key="idx"
              class="issue-item"
              :class="issue.severity"
            >
              <div class="issue-header">
                <el-tag :type="getSeverityType(issue.severity)" size="small">
                  {{ issue.severity }}
                </el-tag>
                <span class="issue-type">{{ issue.type }}</span>
              </div>
              <div class="issue-desc">{{ issue.description }}</div>
              <div class="issue-suggestion" v-if="issue.suggestion">
                <span class="label">建议：</span>{{ issue.suggestion }}
              </div>
            </div>
          </div>
        </el-card>
        
        <!-- 优化建议 -->
        <el-card shadow="never" class="suggestions-card" v-if="detailDialog.data.suggestions?.length">
          <template #header>
            <div class="card-header">
              <span>优化建议</span>
              <el-tag type="primary">{{ detailDialog.data.suggestions.length }} 条</el-tag>
            </div>
          </template>
          <el-table :data="detailDialog.data.suggestions" border>
            <el-table-column prop="type" label="类型" width="120">
              <template #default="{ row: s }">
                <el-tag :type="getSuggestionType(s.type)" size="small">{{ s.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="200" />
            <el-table-column prop="reason" label="原因" min-width="200" />
            <el-table-column prop="expected_improvement" label="预期提升" width="120" />
            <el-table-column prop="index_ddl" label="索引 DDL" min-width="250">
              <template #default="{ row: s }">
                <pre class="ddl-code" v-if="s.index_ddl">{{ s.index_ddl }}</pre>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>
      
      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
        <el-button type="primary" @click="copyAnalysis">复制分析结果</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

const loading = ref(false)
const instances = ref([])
const history = ref([])

const filters = reactive({
  instance_id: null,
  analysis_type: null,
  date_range: null
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const detailDialog = reactive({
  visible: false,
  data: null
})

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    instances.value = (data.items || []).filter(inst => inst.db_type !== 'redis')
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 获取历史记录
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (filters.instance_id) params.instance_id = filters.instance_id
    if (filters.analysis_type) params.analysis_type = filters.analysis_type
    if (filters.date_range && filters.date_range.length === 2) {
      params.start_date = filters.date_range[0]
      params.end_date = filters.date_range[1]
    }
    
    const data = await request.get('/sql-optimization/analysis-history', { params })
    history.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取分析历史失败:', error)
    ElMessage.error('获取分析历史失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.instance_id = null
  filters.analysis_type = null
  filters.date_range = null
  fetchData()
}

// 查看详情
const viewDetail = async (row) => {
  try {
    const data = await request.get(`/sql-optimization/analysis-history/${row.id}`)
    detailDialog.data = data
    detailDialog.visible = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 复制分析结果
const copyAnalysis = async () => {
  if (!detailDialog.data?.analysis_content) return
  
  try {
    await navigator.clipboard.writeText(detailDialog.data.analysis_content)
    ElMessage.success('已复制到剪贴板')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

// 格式化 Markdown（简化版）
const formatMarkdown = (content) => {
  if (!content) return ''
  return content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n/g, '<br>')
}

// 截断 SQL
const truncateSQL = (sql, maxLen) => {
  if (!sql) return '-'
  return sql.length > maxLen ? sql.substring(0, maxLen) + '...' : sql
}

// 获取实例名称
const getInstanceName = (instanceId) => {
  const inst = instances.value.find(i => i.id === instanceId)
  return inst?.name || '-'
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('MM-DD HH:mm') : '-'
}

// 获取严重级别类型
const getSeverityType = (severity) => {
  const types = { critical: 'danger', warning: 'warning', info: 'info' }
  return types[severity] || 'info'
}

// 获取建议类型
const getSuggestionType = (type) => {
  const types = {
    '索引优化': 'primary',
    'SQL改写': 'success',
    '配置调整': 'warning',
    '架构优化': 'danger'
  }
  return types[type] || 'info'
}

// 暴露方法供父组件调用
defineExpose({
  fetchData
})

onMounted(() => {
  fetchInstances()
  fetchData()
})
</script>

<style lang="scss" scoped>
.analysis-history {
  .filter-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    .sql-fingerprint {
      font-family: monospace;
      font-size: 12px;
      color: #606266;
    }
  }
  
  .pagination {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
  }
  
  .history-expand {
    padding: 15px 20px;
    background: #f5f7fa;
    
    .section {
      margin-bottom: 20px;
      
      &:last-child {
        margin-bottom: 0;
      }
      
      .section-title {
        font-weight: bold;
        margin-bottom: 10px;
        color: #303133;
      }
    }
    
    .analysis-content {
      background: white;
      padding: 15px;
      border-radius: 4px;
      line-height: 1.6;
      
      :deep(code) {
        background: #f5f7fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: monospace;
      }
    }
    
    .sql-sample {
      background: white;
      padding: 15px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-all;
      margin: 0;
    }
  }
  
  .detail-content {
    .info-card, .analysis-card, .issues-card, .suggestions-card {
      margin-bottom: 20px;
    }
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .tags {
        display: flex;
        gap: 8px;
      }
    }
    
    .sql-section {
      margin-top: 15px;
      
      .section-label {
        font-weight: bold;
        margin-bottom: 8px;
        color: #606266;
      }
      
      .sql-content {
        background: #f5f7fa;
        padding: 15px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 12px;
        white-space: pre-wrap;
        word-break: break-all;
        margin: 0;
      }
    }
    
    .analysis-content {
      line-height: 1.8;
      
      :deep(code) {
        background: #f5f7fa;
        padding: 2px 6px;
        border-radius: 3px;
        font-family: monospace;
      }
    }
    
    .issues-list {
      .issue-item {
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 8px;
        border-left: 4px solid;
        
        &.critical {
          background: #fef0f0;
          border-color: #f56c6c;
        }
        
        &.warning {
          background: #fdf6ec;
          border-color: #e6a23c;
        }
        
        &.info {
          background: #f4f4f5;
          border-color: #909399;
        }
        
        .issue-header {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
          
          .issue-type {
            font-weight: bold;
          }
        }
        
        .issue-desc {
          color: #606266;
          margin-bottom: 8px;
        }
        
        .issue-suggestion {
          font-size: 12px;
          color: #409eff;
          
          .label {
            color: #909399;
          }
        }
      }
    }
    
    .ddl-code {
      margin: 0;
      font-family: monospace;
      font-size: 12px;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}
</style>
