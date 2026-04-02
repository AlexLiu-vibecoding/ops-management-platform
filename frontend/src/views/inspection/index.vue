<template>
  <div class="inspection-page">
    <!-- 标签页 -->
    <el-tabs v-model="activeTab" class="tabs-container">
      <!-- 执行巡检 -->
      <el-tab-pane label="执行巡检" name="run">
        <el-card shadow="never">
          <el-form :model="runForm" label-width="100px">
            <el-form-item label="选择实例">
              <el-select v-model="runForm.instance_id" placeholder="请选择实例" style="width: 300px">
                <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="巡检模块">
              <el-checkbox-group v-model="runForm.modules">
                <el-checkbox value="slow_query">慢查询</el-checkbox>
                <el-checkbox value="index">索引分析</el-checkbox>
                <el-checkbox value="lock">锁等待</el-checkbox>
                <el-checkbox value="transaction">长事务</el-checkbox>
                <el-checkbox value="repl">主从复制</el-checkbox>
                <el-checkbox value="capacity">容量分析</el-checkbox>
              </el-checkbox-group>
              <div class="form-tip">不选择则检查全部模块</div>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="runInspection" :loading="running">开始巡检</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 巡检结果 -->
        <el-card v-if="inspectionResult" shadow="never" class="result-card">
          <template #header>
            <div class="card-header">
              <span>巡检结果 - {{ inspectionResult.instance_name }}</span>
              <el-tag>{{ inspectionResult.check_time }}</el-tag>
            </div>
          </template>
          
          <el-row :gutter="20" class="stats-row">
            <el-col :span="6">
              <div class="stat-item normal">
                <div class="stat-value">{{ inspectionResult.normal_count }}</div>
                <div class="stat-label">正常</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item warning">
                <div class="stat-value">{{ inspectionResult.warning_count }}</div>
                <div class="stat-label">警告</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item critical">
                <div class="stat-value">{{ inspectionResult.critical_count }}</div>
                <div class="stat-label">严重</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-item error">
                <div class="stat-value">{{ inspectionResult.error_count }}</div>
                <div class="stat-label">错误</div>
              </div>
            </el-col>
          </el-row>

          <el-table :data="inspectionResult.results" style="width: 100%">
            <el-table-column prop="module_label" label="模块" width="100" />
            <el-table-column prop="metric_name" label="指标" min-width="150" />
            <el-table-column prop="status_label" label="状态" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actual_value" label="实际值" min-width="120" />
            <el-table-column prop="suggestion" label="建议" min-width="200">
              <template #default="{ row }">
                <span v-if="row.suggestion">{{ row.suggestion }}</span>
                <span v-else class="text-muted">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 巡检指标配置 -->
      <el-tab-pane label="指标配置" name="metrics">
        <el-card shadow="never">
          <div class="toolbar">
            <el-button type="primary" @click="fetchMetrics">刷新</el-button>
          </div>
          
          <el-table :data="metrics" v-loading="loadingMetrics" style="width: 100%">
            <el-table-column prop="module_label" label="模块" width="100" />
            <el-table-column prop="metric_name" label="指标名称" min-width="150" />
            <el-table-column prop="metric_code" label="指标编码" width="150" />
            <el-table-column prop="check_freq" label="检查频率" width="100" align="center" />
            <el-table-column prop="warn_threshold" label="告警阈值" width="100" />
            <el-table-column prop="critical_threshold" label="严重阈值" width="100" />
            <el-table-column prop="is_enabled" label="启用状态" width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="row.is_enabled ? 'success' : 'info'" size="small">
                  {{ row.is_enabled ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 历史记录 -->
      <el-tab-pane label="历史记录" name="history">
        <el-card shadow="never">
          <el-form :inline="true" class="filter-form">
            <el-form-item label="实例">
              <el-select v-model="historyFilters.instance_id" placeholder="全部" clearable style="width: 150px">
                <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="historyFilters.status" placeholder="全部" clearable style="width: 120px">
                <el-option label="正常" value="normal" />
                <el-option label="警告" value="warning" />
                <el-option label="严重" value="critical" />
                <el-option label="错误" value="error" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="fetchHistory">查询</el-button>
            </el-form-item>
          </el-form>

          <el-table :data="historyResults" v-loading="loadingHistory" style="width: 100%">
            <el-table-column prop="instance_name" label="实例" min-width="120" />
            <el-table-column prop="module_label" label="模块" width="100" />
            <el-table-column prop="metric_name" label="指标" min-width="150" />
            <el-table-column prop="status_label" label="状态" min-width="80" align="center">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_label }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="actual_value" label="实际值" min-width="100" />
            <el-table-column prop="check_time" label="检查时间" width="160">
              <template #default="{ row }">{{ formatTime(row.check_time) }}</template>
            </el-table-column>
          </el-table>

          <div class="pagination-container">
            <el-pagination
              v-model:current-page="historyPagination.page"
              v-model:page-size="historyPagination.limit"
              :total="historyPagination.total"
              :page-sizes="[20, 50, 100]"
              layout="total, sizes, prev, pager, next"
              @size-change="fetchHistory"
              @current-change="fetchHistory"
            />
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/index'

const activeTab = ref('run')
const instances = ref([])
const metrics = ref([])
const loadingMetrics = ref(false)
const historyResults = ref([])
const loadingHistory = ref(false)
const running = ref(false)
const inspectionResult = ref(null)

const runForm = reactive({
  instance_id: null,
  modules: []
})

const historyFilters = reactive({
  instance_id: null,
  status: null
})

const historyPagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const fetchInstances = async () => {
  try {
    const res = await request.get('/rdb-instances', { params: { limit: 100 } })
    instances.value = res.items || []
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const fetchMetrics = async () => {
  loadingMetrics.value = true
  try {
    const res = await request.get('/inspection/metrics')
    metrics.value = res.items || []
  } catch (error) {
    console.error('获取指标列表失败:', error)
  } finally {
    loadingMetrics.value = false
  }
}

const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const res = await request.get('/inspection/results', {
      params: {
        ...historyFilters,
        page: historyPagination.page,
        limit: historyPagination.limit
      }
    })
    historyResults.value = res.items || []
    historyPagination.total = res.total || 0
  } catch (error) {
    console.error('获取历史记录失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

const runInspection = async () => {
  if (!runForm.instance_id) {
    ElMessage.warning('请选择实例')
    return
  }
  
  running.value = true
  try {
    const res = await request.post('/inspection/run', {
      instance_id: runForm.instance_id,
      modules: runForm.modules.length > 0 ? runForm.modules : null
    })
    inspectionResult.value = res
    ElMessage.success('巡检完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '巡检失败')
  } finally {
    running.value = false
  }
}

const getStatusType = (status) => {
  const map = { normal: 'success', warning: 'warning', critical: 'danger', error: 'info' }
  return map[status] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  fetchInstances()
  fetchMetrics()
  fetchHistory()
})
</script>

<style lang="scss" scoped>
.inspection-page {
  .tabs-container {
    :deep(.el-tabs__header) {
      margin-bottom: 20px;
    }
  }
  
  .result-card {
    margin-top: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .stats-row {
      margin-bottom: 20px;
      
      .stat-item {
        text-align: center;
        padding: 20px;
        border-radius: 8px;
        
        .stat-value {
          font-size: 32px;
          font-weight: bold;
        }
        
        .stat-label {
          font-size: 14px;
          margin-top: 5px;
        }
        
        &.normal {
          background: #f0f9eb;
          .stat-value, .stat-label { color: #67C23A; }
        }
        
        &.warning {
          background: #fdf6ec;
          .stat-value, .stat-label { color: #E6A23C; }
        }
        
        &.critical {
          background: #fef0f0;
          .stat-value, .stat-label { color: #F56C6C; }
        }
        
        &.error {
          background: #f4f4f5;
          .stat-value, .stat-label { color: #909399; }
        }
      }
    }
  }
  
  .toolbar {
    margin-bottom: 15px;
  }
  
  .filter-form {
    margin-bottom: 15px;
  }
  
  .form-tip {
    font-size: 12px;
    color: #909399;
    margin-top: 5px;
  }
  
  .text-muted {
    color: #909399;
  }
  
  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }
}
</style>
