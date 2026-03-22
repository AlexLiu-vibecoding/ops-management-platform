<template>
  <div class="approvals-center-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>审批中心</span>
            <el-badge v-if="pendingCount > 0" :value="pendingCount" class="pending-badge" />
          </div>
          <el-button @click="fetchApprovals">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane name="pending">
          <template #label>
            <span>待审批</span>
            <el-badge v-if="pendingCount > 0" :value="pendingCount" class="tab-badge" />
          </template>
        </el-tab-pane>
        <el-tab-pane label="已审批" name="processed" />
      </el-tabs>
      
      <el-table :data="approvalList" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="title-cell">
              <span>{{ row.title }}</span>
              <el-tag v-if="row.auto_execute" type="success" size="small" style="margin-left: 6px;">自动</el-tag>
              <el-tag v-if="row.scheduled_time" type="warning" size="small" style="margin-left: 6px;">定时</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="requester_name" label="申请人" width="80" show-overflow-tooltip />
        <el-table-column prop="change_type" label="类型" width="70" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.change_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="instance_name" label="实例" min-width="100" show-overflow-tooltip />
        <el-table-column prop="database_target" label="数据库" min-width="80" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.database_mode === 'all'">
              <el-tag type="warning" size="small">全部</el-tag>
            </span>
            <span v-else>{{ row.database_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sql_risk_level" label="风险" width="60" align="center">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="affected_rows_estimate" label="预估影响" width="80" align="right">
          <template #default="{ row }">
            <span v-if="row.affected_rows_estimate">{{ row.affected_rows_estimate.toLocaleString() }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" @click="handleView(row)">详情</el-button>
              <template v-if="row.status === 'pending'">
                <el-button link type="success" @click="handleApprove(row, true)">通过</el-button>
                <el-button link type="danger" @click="handleApprove(row, false)">拒绝</el-button>
              </template>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="fetchApprovals"
        @current-change="fetchApprovals"
        style="margin-top: 15px; justify-content: flex-end;"
      />
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="变更详情" width="900px">
      <ApprovalDetailCard :approval="detailDialog.data" title="审批详情" />
      
      <!-- 审批操作 -->
      <div v-if="detailDialog.data?.status === 'pending'" class="approval-actions">
        <el-divider />
        <el-form :model="approvalForm" label-width="80px">
          <el-form-item label="审批意见">
            <el-input v-model="approvalForm.comment" type="textarea" :rows="2" placeholder="请输入审批意见（可选）" />
          </el-form-item>
          <el-form-item>
            <el-button type="success" @click="handleApprove(detailDialog.data, true)">通过</el-button>
            <el-button type="danger" @click="handleApprove(detailDialog.data, false)">拒绝</el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import ApprovalDetailCard from '@/components/ApprovalDetailCard.vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const loading = ref(false)
const activeTab = ref('pending')
const approvalList = ref([])
const pendingCount = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const detailDialog = reactive({
  visible: false,
  data: null
})

const approvalForm = reactive({
  comment: ''
})

const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }
    
    if (activeTab.value === 'pending') {
      // 待审批：只显示 status=pending 的记录
      params.status_filter = 'pending'
    } else {
      // 已审批：显示非 pending 状态，且当前用户审批过的记录
      params.except_status = 'pending'
      params.approver_id = currentUserId.value
    }
    
    const data = await request.get('/approvals', { params })
    approvalList.value = data.items || []
    pagination.total = data.total || 0
    
    // 获取待审批数量
    if (activeTab.value === 'pending') {
      pendingCount.value = data.total || 0
    }
  } catch (error) {
    console.error('获取列表失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchPendingCount = async () => {
  try {
    const data = await request.get('/approvals', { params: { status: 'pending', limit: 1 } })
    pendingCount.value = data.total || 0
  } catch (error) {
    console.error('获取待审批数量失败:', error)
  }
}

const handleTabChange = () => {
  pagination.page = 1
  fetchApprovals()
}

const handleView = async (row) => {
  try {
    const data = await request.get(`/approvals/${row.id}`)
    detailDialog.data = data
    approvalForm.comment = ''
    detailDialog.visible = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const handleApprove = async (row, approved) => {
  const action = approved ? '通过' : '拒绝'
  
  try {
    const { value: comment } = await ElMessageBox.prompt(
      `确定要${action}此变更申请吗？`,
      '审批确认',
      {
        confirmButtonText: action,
        cancelButtonText: '取消',
        inputPlaceholder: '请输入审批意见（可选）',
        inputValue: approvalForm.comment,
        type: approved ? 'success' : 'warning'
      }
    )
    
    await request.post(`/approvals/${row.id}/approve`, {
      approved,
      comment: comment || ''
    })
    
    ElMessage.success(`审批${action}成功`)
    detailDialog.visible = false
    fetchApprovals()
    fetchPendingCount()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '审批失败')
    }
  }
}

const getRiskLabel = (level) => {
  const labels = { low: '低', medium: '中', high: '高', critical: '极高' }
  return labels[level] || level
}

const getStatusType = (status) => {
  const types = { pending: 'warning', approved: 'success', rejected: 'danger', executed: 'info', failed: 'danger' }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = { pending: '待审批', approved: '已通过', rejected: '已拒绝', executed: '已执行', failed: '执行失败' }
  return labels[status] || status
}

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'

onMounted(() => {
  fetchApprovals()
  fetchPendingCount()
})
</script>

<style lang="scss" scoped>
.approvals-center-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }
  
  .pending-badge {
    margin-left: 8px;
  }
  
  .tab-badge {
    margin-left: 5px;
  }
  
  .risk-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    &.low { background: #f0f9eb; color: #67c23a; }
    &.medium { background: #fdf6ec; color: #e6a23c; }
    &.high { background: #fef0f0; color: #f56c6c; }
    &.critical { background: #fde2e2; color: #f56c6c; font-weight: bold; }
  }
  
  .title-cell {
    display: flex;
    align-items: center;
  }
  
  .sql-preview {
    background: #f5f7fa;
    padding: 10px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 12px;
    max-height: 200px;
    overflow: auto;
    white-space: pre-wrap;
    margin: 0;
  }
  
  .table-operations {
    display: flex;
    gap: 8px;
  }
  
  .approval-actions {
    margin-top: 15px;
  }
}
</style>
