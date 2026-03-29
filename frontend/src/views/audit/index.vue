<template>
  <div class="audit-page">
    <!-- 筛选区域 -->
    <el-card shadow="never" class="search-card">
      <el-form :inline="true" :model="searchForm">
        <el-form-item label="操作类型">
          <el-select v-model="searchForm.operation_type" placeholder="全部" clearable style="width: 150px;">
            <el-option
              v-for="type in operationTypes"
              :key="type.value"
              :label="type.label"
              :value="type.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="操作用户">
          <el-select v-model="searchForm.user_id" placeholder="全部" clearable style="width: 120px;">
            <el-option
              v-for="user in users"
              :key="user.id"
              :label="user.real_name || user.username"
              :value="user.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="实例">
          <el-select v-model="searchForm.instance_id" placeholder="全部" clearable style="width: 150px;">
            <el-option
              v-for="inst in instances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="时间范围">
          <el-date-picker
            v-model="timeRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 340px;"
            :shortcuts="timeShortcuts"
          />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">重置</el-button>
          <el-button type="success" @click="handleExport" :loading="exporting">
            <el-icon><Download /></el-icon>
            导出
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="logList" style="width: 100%" v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="操作用户" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.username }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation_type_label" label="操作类型" width="140">
          <template #default="{ row }">
            <el-tag :type="getOperationTagType(row.operation_type)" size="small">
              {{ row.operation_type_label || row.operation_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operation_detail" label="操作详情" min-width="250" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="detail-text">{{ row.operation_detail }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="instance_name" label="实例" width="180">
          <template #default="{ row }">
            {{ row.instance_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="request_path" label="请求路径" width="180" show-overflow-tooltip />
        <el-table-column prop="response_code" label="响应码" width="90">
          <template #default="{ row }">
            <el-tag :type="row.response_code === 200 ? 'success' : 'danger'" size="small">
              {{ row.response_code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="request_ip" label="请求IP" width="130">
          <template #default="{ row }">
            {{ row.request_ip || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="操作时间" width="170">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="80" fixed="right">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" size="small" @click="handleViewDetail(row)">详情</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[20, 50, 100, 200]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="fetchLogs"
        @current-change="fetchLogs"
      />
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="操作详情" width="700px">
      <el-descriptions :column="2" border v-if="currentLog">
        <el-descriptions-item label="ID">{{ currentLog.id }}</el-descriptions-item>
        <el-descriptions-item label="操作用户">{{ currentLog.username }}</el-descriptions-item>
        <el-descriptions-item label="操作类型">
          <el-tag :type="getOperationTagType(currentLog.operation_type)" size="small">
            {{ currentLog.operation_type_label || currentLog.operation_type }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="响应码">
          <el-tag :type="currentLog.response_code === 200 ? 'success' : 'danger'" size="small">
            {{ currentLog.response_code }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实例">{{ currentLog.instance_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="环境">{{ currentLog.environment_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求方法">{{ currentLog.request_method }}</el-descriptions-item>
        <el-descriptions-item label="请求IP">{{ currentLog.request_ip || '-' }}</el-descriptions-item>
        <el-descriptions-item label="请求路径" :span="2">{{ currentLog.request_path }}</el-descriptions-item>
        <el-descriptions-item label="操作详情" :span="2">
          <div class="detail-content">{{ currentLog.operation_detail }}</div>
        </el-descriptions-item>
        <el-descriptions-item label="响应消息" :span="2">{{ currentLog.response_message || '-' }}</el-descriptions-item>
        <el-descriptions-item label="执行耗时">{{ currentLog.execution_time ? `${currentLog.execution_time}ms` : '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">{{ formatTime(currentLog.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { auditApi } from '@/api/audit'
import request from '@/api/index'
import { instancesApi } from '@/api/instances'
import { ElMessage } from 'element-plus'
import { Search, Download } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const exporting = ref(false)
const logList = ref([])
const operationTypes = ref([])
const users = ref([])
const instances = ref([])
const timeRange = ref([])
const detailVisible = ref(false)
const currentLog = ref(null)

const searchForm = reactive({
  operation_type: null,
  user_id: null,
  instance_id: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 时间快捷选项
const timeShortcuts = [
  {
    text: '最近1小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 3600 * 1000)
      return [start, end]
    }
  },
  {
    text: '最近24小时',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 24 * 3600 * 1000)
      return [start, end]
    }
  },
  {
    text: '最近7天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 7 * 24 * 3600 * 1000)
      return [start, end]
    }
  },
  {
    text: '最近30天',
    value: () => {
      const end = new Date()
      const start = new Date()
      start.setTime(start.getTime() - 30 * 24 * 3600 * 1000)
      return [start, end]
    }
  }
]

// 获取操作类型标签样式
const getOperationTagType = (type) => {
  const typeMap = {
    'login': '',
    'logout': 'info',
    'create_instance': 'success',
    'update_instance': 'warning',
    'delete_instance': 'danger',
    'execute_sql': 'warning',
    'submit_approval': '',
    'approve': 'success',
    'reject': 'danger',
    'execute_approval': 'warning',
    'scheduled_execute': 'info'
  }
  return typeMap[type] || ''
}

// 获取审计日志列表
const fetchLogs = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...searchForm
    }
    
    // 处理时间范围
    if (timeRange.value && timeRange.value.length === 2) {
      params.start_time = timeRange.value[0]
      params.end_time = timeRange.value[1]
    }
    
    const data = await auditApi.getLogs(params)
    // API 返回格式: {total, page, page_size, data}
    // data 中每条记录包含 operation_type_label 字段
    logList.value = data.data || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取审计日志失败:', error)
  } finally {
    loading.value = false
  }
}

// 获取操作类型列表
const fetchOperationTypes = async () => {
  try {
    // API 返回格式: [{value, label}, ...]
    const data = await auditApi.getOperationTypes()
    operationTypes.value = data || []
  } catch (error) {
    console.error('获取操作类型失败:', error)
  }
}

// 获取用户列表
const fetchUsers = async () => {
  try {
    const data = await request.get('/users')
    users.value = data.items || data || []
  } catch (error) {
    console.error('获取用户列表失败:', error)
  }
}

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 100 })
    instances.value = data.items || data || []
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchLogs()
}

// 重置
const handleReset = () => {
  searchForm.operation_type = null
  searchForm.user_id = null
  searchForm.instance_id = null
  timeRange.value = []
  handleSearch()
}

// 查看详情
const handleViewDetail = (row) => {
  currentLog.value = row
  detailVisible.value = true
}

// 导出
const handleExport = async () => {
  exporting.value = true
  try {
    const params = { ...searchForm }
    if (timeRange.value && timeRange.value.length === 2) {
      params.start_time = timeRange.value[0]
      params.end_time = timeRange.value[1]
    }
    
    const blob = await auditApi.exportLogs(params)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audit_logs_${dayjs().format('YYYYMMDD_HHmmss')}.csv`
    link.click()
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('导出成功')
  } catch (error) {
    console.error('导出失败:', error)
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchLogs()
  fetchOperationTypes()
  fetchUsers()
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.audit-page {
  .search-card {
    margin-bottom: 20px;
  }
  
  .table-card {
    .el-pagination {
      margin-top: 20px;
      justify-content: flex-end;
    }
  }
  
  .detail-text {
    font-size: 13px;
    color: #606266;
  }
  
  .detail-content {
    max-height: 200px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: monospace;
    font-size: 13px;
    background: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
  }
}
</style>
