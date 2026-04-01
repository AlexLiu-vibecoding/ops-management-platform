<template>
  <div class="notification-logs-page">
    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <div class="stat-content">
            <div class="stat-value">{{ stats.total }}</div>
            <div class="stat-label">总计</div>
          </div>
          <el-icon class="stat-icon"><Message /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card success">
          <div class="stat-content">
            <div class="stat-value">{{ stats.success }}</div>
            <div class="stat-label">成功</div>
          </div>
          <el-icon class="stat-icon"><CircleCheck /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card danger">
          <div class="stat-content">
            <div class="stat-value">{{ stats.failed }}</div>
            <div class="stat-label">失败</div>
          </div>
          <el-icon class="stat-icon"><CircleClose /></el-icon>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card warning">
          <div class="stat-content">
            <div class="stat-value">{{ stats.pending }}</div>
            <div class="stat-label">待发送</div>
          </div>
          <el-icon class="stat-icon"><Clock /></el-icon>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选条件 -->
    <el-card shadow="never" class="filter-card">
      <el-form :inline="true" :model="filters" class="filter-form">
        <el-form-item label="通知类型">
          <el-select v-model="filters.notification_type" placeholder="全部类型" clearable style="width: 120px">
            <el-option label="审批通知" value="approval" />
            <el-option label="告警通知" value="alert" />
            <el-option label="定时任务" value="scheduled_task" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable style="width: 100px">
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
            <el-option label="待发送" value="pending" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知通道">
          <el-select v-model="filters.channel_id" placeholder="全部通道" clearable style="width: 150px">
            <el-option 
              v-for="channel in channels" 
              :key="channel.id" 
              :label="channel.name" 
              :value="channel.id" 
            />
          </el-select>
        </el-form-item>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="filters.dateRange"
            type="daterange"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            format="YYYY-MM-DD"
            value-format="YYYY-MM-DD"
            style="width: 240px"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input 
            v-model="filters.keyword" 
            placeholder="搜索标题/内容" 
            clearable 
            style="width: 200px"
            @keyup.enter="loadLogs"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadLogs">查询</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 通知列表 -->
    <el-card shadow="never" class="table-card">
      <template #header>
        <div class="card-header">
          <span>通知历史记录</span>
          <el-popconfirm
            title="确定清理30天前的历史记录吗？"
            @confirm="clearHistory"
          >
            <template #reference>
              <el-button type="danger" text>
                <el-icon><Delete /></el-icon>
                清理历史
              </el-button>
            </template>
          </el-popconfirm>
        </div>
      </template>

      <el-table 
        :data="logs" 
        style="width: 100%" 
        v-loading="loading"
        @row-click="showDetail"
        class="clickable-table"
      >
        <el-table-column prop="notification_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTypeTag(row.notification_type)" size="small">
              {{ getTypeName(row.notification_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sub_type" label="细分类型" width="100" align="center">
          <template #default="{ row }">
            <span v-if="row.sub_type">{{ row.sub_type }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="channel_name" label="通知通道" min-width="120">
          <template #default="{ row }">
            <span v-if="row.channel_name">{{ row.channel_name }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.title" placement="top" :disabled="row.title.length < 30">
              <span class="truncate-text">{{ row.title }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusTag(row.status)" size="small">
              {{ getStatusName(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sent_at" label="发送时间" width="160">
          <template #default="{ row }">
            <span v-if="row.sent_at">{{ formatTime(row.sent_at) }}</span>
            <span v-else class="text-gray-400">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" text size="small" @click.stop="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadLogs"
          @current-change="loadLogs"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialog.visible"
      title="通知详情"
      width="600px"
      destroy-on-close
    >
      <el-descriptions :column="2" border v-if="detailDialog.data">
        <el-descriptions-item label="通知类型">
          <el-tag :type="getTypeTag(detailDialog.data.notification_type)" size="small">
            {{ getTypeName(detailDialog.data.notification_type) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="细分类型">
          {{ detailDialog.data.sub_type || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="通知通道">
          {{ detailDialog.data.channel_name || '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusTag(detailDialog.data.status)" size="small">
            {{ getStatusName(detailDialog.data.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="标题" :span="2">
          {{ detailDialog.data.title }}
        </el-descriptions-item>
        <el-descriptions-item label="内容" :span="2">
          <pre class="content-pre">{{ detailDialog.data.content || '-' }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="响应码" v-if="detailDialog.data.response_code">
          {{ detailDialog.data.response_code }}
        </el-descriptions-item>
        <el-descriptions-item label="错误信息" :span="2" v-if="detailDialog.data.error_message">
          <span class="error-text">{{ detailDialog.data.error_message }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="发送时间">
          {{ detailDialog.data.sent_at ? formatTime(detailDialog.data.sent_at) : '-' }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatTime(detailDialog.data.created_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Message, CircleCheck, CircleClose, Clock, Delete } from '@element-plus/icons-vue'
import request from '@/api/index'
import { formatTime } from '@/utils/format'

// 统计数据
const stats = ref({
  total: 0,
  success: 0,
  failed: 0,
  pending: 0,
  by_type: {},
  by_channel: {}
})

// 筛选条件
const filters = reactive({
  notification_type: '',
  status: '',
  channel_id: '',
  dateRange: null,
  keyword: ''
})

// 分页
const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// 列表数据
const logs = ref([])
const loading = ref(false)

// 通道列表
const channels = ref([])

// 详情对话框
const detailDialog = reactive({
  visible: false,
  data: null
})

// 加载统计数据
const loadStats = async () => {
  try {
    const res = await request.get('/notification-logs/stats', { params: { days: 7 } })
    if (res.code === 0) {
      stats.value = res.data
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
  }
}

// 加载通知列表
const loadLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    
    if (filters.notification_type) {
      params.notification_type = filters.notification_type
    }
    if (filters.status) {
      params.status = filters.status
    }
    if (filters.channel_id) {
      params.channel_id = filters.channel_id
    }
    if (filters.keyword) {
      params.keyword = filters.keyword
    }
    if (filters.dateRange && filters.dateRange.length === 2) {
      params.start_date = filters.dateRange[0]
      params.end_date = filters.dateRange[1]
    }
    
    const res = await request.get('/notification-logs', { params })
    if (res.code === 0) {
      logs.value = res.data.items
      pagination.total = res.data.total
    }
  } catch (error) {
    console.error('加载通知列表失败:', error)
    ElMessage.error('加载通知列表失败')
  } finally {
    loading.value = false
  }
}

// 加载通道列表
const loadChannels = async () => {
  try {
    const res = await request.get('/dingtalk/channels')
    if (res.code === 0) {
      channels.value = res.data
    }
  } catch (error) {
    console.error('加载通道列表失败:', error)
  }
}

// 重置筛选条件
const resetFilters = () => {
  filters.notification_type = ''
  filters.status = ''
  filters.channel_id = ''
  filters.dateRange = null
  filters.keyword = ''
  pagination.page = 1
  loadLogs()
}

// 显示详情
const showDetail = (row) => {
  detailDialog.data = row
  detailDialog.visible = true
}

// 清理历史记录
const clearHistory = async () => {
  try {
    const res = await request.post('/notification-logs/clear')
    if (res.code === 0) {
      ElMessage.success(res.message)
      loadLogs()
      loadStats()
    } else {
      ElMessage.error(res.message)
    }
  } catch (error) {
    console.error('清理历史记录失败:', error)
    ElMessage.error('清理历史记录失败')
  }
}

// 类型映射
const getTypeTag = (type) => {
  const map = {
    'approval': 'primary',
    'alert': 'danger',
    'scheduled_task': 'warning'
  }
  return map[type] || ''
}

const getTypeName = (type) => {
  const map = {
    'approval': '审批通知',
    'alert': '告警通知',
    'scheduled_task': '定时任务'
  }
  return map[type] || type
}

// 状态映射
const getStatusTag = (status) => {
  const map = {
    'success': 'success',
    'failed': 'danger',
    'pending': 'warning'
  }
  return map[status] || ''
}

const getStatusName = (status) => {
  const map = {
    'success': '成功',
    'failed': '失败',
    'pending': '待发送'
  }
  return map[status] || status
}

onMounted(() => {
  loadStats()
  loadLogs()
  loadChannels()
})
</script>

<style scoped>
.notification-logs-page {
  padding: 20px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
}

.stat-card .stat-content {
  display: flex;
  flex-direction: column;
}

.stat-card .stat-value {
  font-size: 28px;
  font-weight: bold;
  color: var(--el-text-color-primary);
}

.stat-card .stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.stat-card .stat-icon {
  font-size: 40px;
  color: var(--el-color-primary);
  opacity: 0.3;
}

.stat-card.success .stat-icon {
  color: var(--el-color-success);
}

.stat-card.danger .stat-icon {
  color: var(--el-color-danger);
}

.stat-card.warning .stat-icon {
  color: var(--el-color-warning);
}

.filter-card {
  margin-bottom: 20px;
}

.filter-form {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.table-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.clickable-table :deep(.el-table__row) {
  cursor: pointer;
}

.clickable-table :deep(.el-table__row:hover) {
  background-color: var(--el-fill-color-light);
}

.truncate-text {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.content-pre {
  margin: 0;
  padding: 10px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 200px;
  overflow-y: auto;
}

.error-text {
  color: var(--el-color-danger);
}

.text-gray-400 {
  color: var(--el-text-color-placeholder);
}
</style>
