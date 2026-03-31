<template>
  <div class="optimization-suggestions">
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
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable @change="fetchData" style="width: 140px;">
            <el-option label="待处理" value="pending" />
            <el-option label="已采用" value="adopted" />
            <el-option label="已拒绝" value="rejected" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="filters.risk_level" placeholder="全部" clearable @change="fetchData" style="width: 120px;">
            <el-option label="低" value="low" />
            <el-option label="中" value="medium" />
            <el-option label="高" value="high" />
          </el-select>
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
    
    <!-- 建议列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>优化建议</span>
          <div class="header-actions">
            <el-tag :type="stats.pending > 0 ? 'warning' : 'success'">
              待处理: {{ stats.pending }}
            </el-tag>
            <el-tag type="success">已采用: {{ stats.adopted }}</el-tag>
          </div>
        </div>
      </template>
      
      <el-table :data="suggestions" v-loading="loading" style="width: 100%">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="suggestion-expand">
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="SQL 样例" :span="2">
                  <pre class="sql-sample">{{ row.sql_sample || '-' }}</pre>
                </el-descriptions-item>
                <el-descriptions-item label="建议的索引 DDL" :span="2" v-if="row.index_ddl">
                  <pre class="sql-ddl">{{ row.index_ddl }}</pre>
                </el-descriptions-item>
                <el-descriptions-item label="回滚 SQL" :span="2" v-if="row.rollback_sql">
                  <pre class="sql-ddl">{{ row.rollback_sql }}</pre>
                </el-descriptions-item>
              </el-descriptions>
              
              <!-- 问题列表 -->
              <div class="issues-section" v-if="row.issues?.length">
                <div class="section-title">发现的问题</div>
                <el-tag
                  v-for="(issue, idx) in row.issues"
                  :key="idx"
                  :type="getSeverityType(issue.severity)"
                  class="issue-tag"
                >
                  {{ issue.type }}: {{ issue.description }}
                </el-tag>
              </div>
              
              <!-- 建议列表 -->
              <div class="suggestions-section" v-if="row.suggestions?.length">
                <div class="section-title">优化建议</div>
                <div v-for="(s, idx) in row.suggestions" :key="idx" class="suggestion-item">
                  <el-tag :type="getPriorityType(s.priority)" size="small">{{ s.type }}</el-tag>
                  <span class="suggestion-desc">{{ s.description }}</span>
                </div>
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
        
        <el-table-column label="风险等级" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getRiskLevelType(row.risk_level)" size="small">
              {{ getRiskLevelLabel(row.risk_level) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="预期提升" width="100">
          <template #default="{ row }">
            <span class="improvement" v-if="row.expected_improvement">{{ row.expected_improvement }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column label="实际提升" width="100">
          <template #default="{ row }">
            <span class="actual-improvement" v-if="row.actual_improvement">
              {{ row.actual_improvement.toFixed(1) }}%
            </span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="created_at" label="创建时间" width="140">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="primary" size="small" @click="adoptSuggestion(row)" :loading="row.adopting">
                采用
              </el-button>
              <el-button size="small" @click="showRejectDialog(row)">拒绝</el-button>
            </template>
            <template v-else-if="row.status === 'adopted'">
              <el-button type="success" size="small" link @click="viewApproval(row)">
                查看变更
              </el-button>
              <el-button size="small" @click="verifySuggestion(row)" :loading="row.verifying">
                验证效果
              </el-button>
            </template>
            <template v-else>
              <el-tag type="info" size="small">已处理</el-tag>
            </template>
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
    
    <!-- 拒绝对话框 -->
    <el-dialog v-model="rejectDialog.visible" title="拒绝建议" width="500px">
      <el-form :model="rejectDialog" label-width="80px">
        <el-form-item label="拒绝原因">
          <el-input
            v-model="rejectDialog.reason"
            type="textarea"
            :rows="3"
            placeholder="请输入拒绝原因（可选）"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="rejectDialog.visible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="rejectDialog.loading">
          确认拒绝
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

const loading = ref(false)
const instances = ref([])
const suggestions = ref([])

const filters = reactive({
  instance_id: null,
  status: null,
  risk_level: null
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const stats = computed(() => {
  const pending = suggestions.value.filter(s => s.status === 'pending').length
  const adopted = suggestions.value.filter(s => s.status === 'adopted').length
  return { pending, adopted }
})

const rejectDialog = reactive({
  visible: false,
  loading: false,
  suggestion: null,
  reason: ''
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

// 获取优化建议列表
const fetchData = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    if (filters.instance_id) params.instance_id = filters.instance_id
    if (filters.status) params.status = filters.status
    if (filters.risk_level) params.risk_level = filters.risk_level
    
    const data = await request.get('/sql-optimization/suggestions', { params })
    suggestions.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取优化建议失败:', error)
    ElMessage.error('获取优化建议失败')
  } finally {
    loading.value = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.instance_id = null
  filters.status = null
  filters.risk_level = null
  fetchData()
}

// 采用建议
const adoptSuggestion = async (row) => {
  if (!row.index_ddl && !row.suggested_sql) {
    ElMessage.warning('该建议没有可执行的 SQL 语句')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      '采用建议后将创建变更申请，是否继续？',
      '确认采用',
      { type: 'warning' }
    )
    
    row.adopting = true
    const data = await request.post(`/sql-optimization/suggestions/${row.id}/adopt`)
    ElMessage.success(data.message || '已创建变更申请')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.message || '采用失败')
    }
  } finally {
    row.adopting = false
  }
}

// 显示拒绝对话框
const showRejectDialog = (row) => {
  rejectDialog.suggestion = row
  rejectDialog.reason = ''
  rejectDialog.visible = true
}

// 确认拒绝
const confirmReject = async () => {
  rejectDialog.loading = true
  try {
    await request.post(
      `/sql-optimization/suggestions/${rejectDialog.suggestion.id}/reject`,
      { reason: rejectDialog.reason }
    )
    ElMessage.success('已拒绝该建议')
    rejectDialog.visible = false
    fetchData()
  } catch (error) {
    ElMessage.error('拒绝失败')
  } finally {
    rejectDialog.loading = false
  }
}

// 查看变更申请
const viewApproval = (row) => {
  if (row.approval_id) {
    window.location.href = `/change/requests?id=${row.approval_id}`
  }
}

// 验证效果
const verifySuggestion = async (row) => {
  row.verifying = true
  try {
    const data = await request.post(`/sql-optimization/suggestions/${row.id}/verify`)
    ElMessage.success(data.message || '验证完成')
    fetchData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '验证失败')
  } finally {
    row.verifying = false
  }
}

// 获取实例名称
const getInstanceName = (instanceId) => {
  const inst = instances.value.find(i => i.id === instanceId)
  return inst?.name || '-'
}

// 截断 SQL
const truncateSQL = (sql, maxLen) => {
  if (!sql) return '-'
  return sql.length > maxLen ? sql.substring(0, maxLen) + '...' : sql
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('MM-DD HH:mm') : '-'
}

// 获取风险等级类型
const getRiskLevelType = (level) => {
  const types = { low: 'success', medium: 'warning', high: 'danger' }
  return types[level] || 'info'
}

// 获取风险等级标签
const getRiskLevelLabel = (level) => {
  const labels = { low: '低', medium: '中', high: '高' }
  return labels[level] || level
}

// 获取状态类型
const getStatusType = (status) => {
  const types = { pending: 'warning', adopted: 'success', rejected: 'danger', expired: 'info' }
  return types[status] || 'info'
}

// 获取状态标签
const getStatusLabel = (status) => {
  const labels = { pending: '待处理', adopted: '已采用', rejected: '已拒绝', expired: '已过期' }
  return labels[status] || status
}

// 获取严重级别类型
const getSeverityType = (severity) => {
  const types = { critical: 'danger', warning: 'warning', info: 'info' }
  return types[severity] || 'info'
}

// 获取优先级类型
const getPriorityType = (priority) => {
  const types = { high: 'danger', medium: 'warning', low: 'info' }
  return types[priority] || 'info'
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
.optimization-suggestions {
  .filter-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-actions {
        display: flex;
        gap: 10px;
      }
    }
    
    .sql-fingerprint {
      font-family: monospace;
      font-size: 12px;
      color: #606266;
    }
    
    .improvement {
      color: #67c23a;
      font-weight: 500;
    }
    
    .actual-improvement {
      color: #409eff;
      font-weight: 500;
    }
  }
  
  .pagination {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
  }
  
  .suggestion-expand {
    padding: 15px 20px;
    background: #f5f7fa;
    
    .sql-sample, .sql-ddl {
      font-family: monospace;
      font-size: 12px;
      margin: 0;
      white-space: pre-wrap;
      word-break: break-all;
    }
    
    .sql-ddl {
      color: #409eff;
    }
    
    .issues-section, .suggestions-section {
      margin-top: 15px;
      
      .section-title {
        font-weight: bold;
        margin-bottom: 10px;
        color: #606266;
      }
      
      .issue-tag {
        margin-right: 8px;
        margin-bottom: 8px;
      }
      
      .suggestion-item {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        
        .suggestion-desc {
          font-size: 13px;
          color: #606266;
        }
      }
    }
  }
}
</style>
