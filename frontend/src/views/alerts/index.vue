<template>
  <div class="alerts-page">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value critical">{{ stats.critical }}</div>
            <div class="stat-label">严重告警</div>
          </div>
          <el-icon class="stat-icon" :size="40"><WarningFilled /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value warning">{{ stats.warning }}</div>
            <div class="stat-label">警告告警</div>
          </div>
          <el-icon class="stat-icon" :size="40"><Warning /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value pending">{{ stats.pending }}</div>
            <div class="stat-label">待处理</div>
          </div>
          <el-icon class="stat-icon" :size="40"><Clock /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-value resolved">{{ stats.resolved }}</div>
            <div class="stat-label">已解决</div>
          </div>
          <el-icon class="stat-icon" :size="40"><CircleCheck /></el-icon>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选条件 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="实例">
          <el-select v-model="filters.instance_id" placeholder="全部实例" clearable style="width: 150px">
            <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="告警级别">
          <el-select v-model="filters.alert_level" placeholder="全部级别" clearable style="width: 120px">
            <el-option label="严重" value="critical" />
            <el-option label="警告" value="warning" />
            <el-option label="信息" value="info" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 120px">
            <el-option label="待处理" value="pending" />
            <el-option label="已确认" value="acknowledged" />
            <el-option label="已解决" value="resolved" />
            <el-option label="已忽略" value="ignored" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="filters.timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            style="width: 360px"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchAlerts">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="alerts" v-loading="loading" style="width: 100%" :show-overflow-tooltip="false">
        <el-table-column prop="instance_name" label="实例" min-width="120" />
        <el-table-column prop="metric_type_label" label="指标类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.metric_type_label }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_level_label" label="级别" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getLevelType(row.alert_level)" size="small">
              {{ row.alert_level_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="alert_title" label="告警标题" min-width="200" />
        <el-table-column prop="status_label" label="状态" min-width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ row.status_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="告警时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
              <el-button v-if="row.status === 'pending'" link type="warning" size="small" @click="acknowledgeAlert(row)">确认</el-button>
              <el-button v-if="row.status !== 'resolved' && row.status !== 'ignored'" link type="success" size="small" @click="resolveAlert(row)">解决</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchAlerts"
          @current-change="fetchAlerts"
        />
      </div>
    </el-card>

    <!-- 告警详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="告警详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="实例">{{ detailDialog.data.instance_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="指标类型">{{ detailDialog.data.metric_type_label }}</el-descriptions-item>
        <el-descriptions-item label="告警级别">
          <el-tag :type="getLevelType(detailDialog.data.alert_level)" size="small">
            {{ detailDialog.data.alert_level_label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailDialog.data.status)" size="small">
            {{ detailDialog.data.status_label }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="告警时间" :span="2">{{ formatTime(detailDialog.data.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="告警标题" :span="2">{{ detailDialog.data.alert_title }}</el-descriptions-item>
        <el-descriptions-item label="告警内容" :span="2">
          <pre class="alert-content">{{ detailDialog.data.alert_content || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.acknowledged_by_name" label="确认人">
          {{ detailDialog.data.acknowledged_by_name }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.acknowledged_at" label="确认时间">
          {{ formatTime(detailDialog.data.acknowledged_at) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.resolved_by_name" label="解决人">
          {{ detailDialog.data.resolved_by_name }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.resolved_at" label="解决时间">
          {{ formatTime(detailDialog.data.resolved_at) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.resolve_note" label="解决说明" :span="2">
          {{ detailDialog.data.resolve_note }}
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
        <el-button v-if="detailDialog.data.status === 'pending'" type="warning" @click="acknowledgeAlert(detailDialog.data); detailDialog.visible = false">确认告警</el-button>
        <el-button v-if="detailDialog.data.status !== 'resolved'" type="success" @click="resolveAlert(detailDialog.data); detailDialog.visible = false">解决告警</el-button>
      </template>
    </el-dialog>

    <!-- 解决告警对话框 -->
    <el-dialog v-model="resolveDialog.visible" title="解决告警" width="400px">
      <el-form>
        <el-form-item label="解决说明">
          <el-input v-model="resolveDialog.note" type="textarea" :rows="3" placeholder="请输入解决说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resolveDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="doResolve" :loading="resolveDialog.loading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { WarningFilled, Warning, Clock, CircleCheck } from '@element-plus/icons-vue'
import request from '@/api/index'

// 数据
const alerts = ref([])
const instances = ref([])
const stats = ref({ total: 0, pending: 0, acknowledged: 0, resolved: 0, critical: 0, warning: 0, info: 0 })
const loading = ref(false)

// 筛选条件
const filters = reactive({
  instance_id: null,
  alert_level: null,
  status: null,
  timeRange: null
})

// 分页
const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

// 详情对话框
const detailDialog = reactive({
  visible: false,
  data: {}
})

// 解决对话框
const resolveDialog = reactive({
  visible: false,
  alertId: null,
  note: '',
  loading: false
})

// 获取告警列表
const fetchAlerts = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit,
      ...filters,
      start_time: filters.timeRange?.[0]?.toISOString(),
      end_time: filters.timeRange?.[1]?.toISOString()
    }
    delete params.timeRange
    
    const res = await request.get('/alerts', { params })
    alerts.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取告警列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 获取统计数据
const fetchStats = async () => {
  try {
    const res = await request.get('/alerts/stats', { params: { days: 7 } })
    stats.value = res
  } catch (error) {
    console.error('获取统计数据失败:', error)
  }
}

// 获取实例列表
const fetchInstances = async () => {
  try {
    const res = await request.get('/instances', { params: { limit: 100 } })
    instances.value = res.items || []
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 查看详情
const viewDetail = async (row) => {
  try {
    const res = await request.get(`/alerts/${row.id}`)
    detailDialog.data = res
    detailDialog.visible = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 确认告警
const acknowledgeAlert = (row) => {
  ElMessageBox.confirm('确认该告警?', '提示', { type: 'warning' }).then(async () => {
    try {
      await request.post(`/alerts/${row.id}/acknowledge`, { note: '' })
      ElMessage.success('告警已确认')
      fetchAlerts()
      fetchStats()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    }
  }).catch(() => {})
}

// 解决告警
const resolveAlert = (row) => {
  resolveDialog.alertId = row.id
  resolveDialog.note = ''
  resolveDialog.visible = true
}

// 执行解决
const doResolve = async () => {
  if (!resolveDialog.note) {
    ElMessage.warning('请输入解决说明')
    return
  }
  
  resolveDialog.loading = true
  try {
    await request.post(`/alerts/${resolveDialog.alertId}/resolve`, { note: resolveDialog.note })
    ElMessage.success('告警已解决')
    resolveDialog.visible = false
    fetchAlerts()
    fetchStats()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    resolveDialog.loading = false
  }
}

// 重置筛选
const resetFilters = () => {
  filters.instance_id = null
  filters.alert_level = null
  filters.status = null
  filters.timeRange = null
  fetchAlerts()
}

// 辅助函数
const getLevelType = (level) => {
  const map = { critical: 'danger', warning: 'warning', info: 'info' }
  return map[level] || 'info'
}

const getStatusType = (status) => {
  const map = { pending: 'warning', acknowledged: 'primary', resolved: 'success', ignored: 'info' }
  return map[status] || 'info'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  fetchInstances()
  fetchAlerts()
  fetchStats()
})
</script>

<style lang="scss" scoped>
.alerts-page {
  .stats-row {
    margin-bottom: 20px;
    
    .stat-card {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .stat-content {
        .stat-value {
          font-size: 28px;
          font-weight: bold;
          
          &.critical { color: #F56C6C; }
          &.warning { color: #E6A23C; }
          &.pending { color: #E6A23C; }
          &.resolved { color: #67C23A; }
        }
        
        .stat-label {
          font-size: 14px;
          color: #909399;
          margin-top: 5px;
        }
      }
      
      .stat-icon {
        color: #DCDFE6;
      }
    }
  }
  
  .filter-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    .pagination-container {
      display: flex;
      justify-content: flex-end;
      margin-top: 20px;
    }
  }
  
  .alert-content {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: monospace;
    font-size: 12px;
    background: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    max-height: 200px;
    overflow-y: auto;
  }
  
  .table-operations {
    display: flex;
    gap: 8px;
    justify-content: center;
  }
}
</style>
