<template>
  <div class="redis-requests-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>Redis 变更</span>
            <el-tag type="danger" size="small" style="margin-left: 10px;">Redis 专用</el-tag>
          </div>
          <div class="header-right">
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              提交 Redis 变更
            </el-button>
          </div>
        </div>
      </template>
      
      <!-- Tab 切换 -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane name="myRequests">
          <template #label>
            <span>我的申请</span>
          </template>
        </el-tab-pane>
        <el-tab-pane v-if="canApprove" name="pendingApproval">
          <template #label>
            <span>待审批</span>
            <el-badge v-if="pendingCount > 0" :value="pendingCount" class="tab-badge" />
          </template>
        </el-tab-pane>
        <el-tab-pane v-if="canApprove" name="processed">
          <template #label>
            <span>已审批</span>
          </template>
        </el-tab-pane>
      </el-tabs>
      
      <!-- 快速筛选 -->
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 120px;" @change="fetchApprovals">
          <el-option label="全部" value="" />
          <el-option label="待审批" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="已执行" value="executed" />
        </el-select>
        <el-button @click="fetchApprovals">刷新</el-button>
      </div>
      
      <el-table :data="approvalList" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="instance_name" label="Redis 实例" min-width="120" show-overflow-tooltip />
        <el-table-column prop="sql_line_count" label="命令行数" width="90" align="center" />
        <el-table-column prop="sql_risk_level" label="风险等级" width="90" align="center">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
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
              <!-- 待审批状态：审批人可操作 -->
              <template v-if="row.status === 'pending' && canApprove">
                <el-button link type="success" @click="handleApprove(row, true)">通过</el-button>
                <el-button link type="danger" @click="handleApprove(row, false)">拒绝</el-button>
              </template>
              <!-- 已通过且非自动执行：可手动执行 -->
              <el-button
                v-if="row.status === 'approved' && !row.auto_execute && !row.scheduled_time"
                link
                type="success"
                @click="handleExecute(row)"
              >
                执行
              </el-button>
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
    
    <!-- 提交变更对话框 -->
    <el-dialog v-model="dialog.visible" title="提交 Redis 变更申请" width="800px" :close-on-click-modal="false">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="dialog.form.title" placeholder="请输入变更标题" maxlength="100" show-word-limit />
        </el-form-item>
        
        <el-form-item label="Redis 实例" prop="instance_id">
          <el-select v-model="dialog.form.instance_id" placeholder="请选择 Redis 实例" style="width: 100%;">
            <el-option v-for="inst in redisInstances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="Redis 命令" prop="sql_content">
          <div class="cmd-input-wrapper">
            <div class="cmd-tips">
              <el-tag type="info" size="small">每行一条命令，如: SET key value</el-tag>
              <el-tag type="warning" size="small">高风险命令(FLUSHALL/FLUSHDB)将被拒绝</el-tag>
            </div>
            <el-input
              v-model="dialog.form.sql_content"
              type="textarea"
              :rows="10"
              placeholder="输入 Redis 命令，每行一条，例如:
SET user:1:name 张三
SET user:1:age 25
INCR counter
EXPIRE user:1:name 3600"
              style="font-family: monospace;"
            />
          </div>
        </el-form-item>
        
        <el-form-item label="备注">
          <el-input v-model="dialog.form.remark" type="textarea" :rows="2" placeholder="请输入备注信息（可选）" />
        </el-form-item>
        
        <el-form-item label="执行方式">
          <el-radio-group v-model="dialog.form.execution_mode">
            <el-radio value="manual">手动执行</el-radio>
            <el-radio value="auto">审批后自动执行</el-radio>
            <el-radio value="scheduled">定时执行</el-radio>
          </el-radio-group>
          <div v-if="dialog.form.execution_mode === 'scheduled'" style="margin-top: 8px;">
            <el-date-picker v-model="dialog.form.scheduled_time" type="datetime" placeholder="选择执行时间" />
          </div>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">提交申请</el-button>
      </template>
    </el-dialog>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="变更详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ detailDialog.data?.title }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailDialog.data?.status)">{{ getStatusLabel(detailDialog.data?.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实例">{{ detailDialog.data?.instance_name }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <span class="risk-tag" :class="detailDialog.data?.sql_risk_level">{{ getRiskLabel(detailDialog.data?.sql_risk_level) }}</span>
        </el-descriptions-item>
        <el-descriptions-item label="提交人">{{ detailDialog.data?.requester_name }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(detailDialog.data?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="命令内容" :span="2">
          <pre class="cmd-preview">{{ detailDialog.data?.sql_content }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="回滚命令" :span="2" v-if="detailDialog.data?.rollback_sql">
          <pre class="cmd-preview rollback">{{ detailDialog.data?.rollback_sql }}</pre>
        </el-descriptions-item>
        <el-descriptions-item label="执行结果" :span="2" v-if="detailDialog.data?.execute_result">
          <pre class="cmd-preview">{{ detailDialog.data?.execute_result }}</pre>
        </el-descriptions-item>
      </el-descriptions>
      
      <!-- 审批操作（待审批状态且是审批人） -->
      <div v-if="detailDialog.data?.status === 'pending' && canApprove" class="approval-actions">
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
import { Plus } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)
const userRole = computed(() => userStore.user?.role)

// 是否有审批权限
const canApprove = computed(() => ['super_admin', 'approval_admin'].includes(userRole.value))

const loading = ref(false)
const approvalList = ref([])
const redisInstances = ref([])
const formRef = ref(null)
const statusFilter = ref('')
const activeTab = ref('myRequests')
const pendingCount = ref(0)

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  submitting: false,
  form: {
    title: '',
    instance_id: null,
    sql_content: '',
    remark: '',
    execution_mode: 'auto',  // 默认审批后自动执行
    scheduled_time: null
  },
  rules: {
    title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
    instance_id: [{ required: true, message: '请选择实例', trigger: 'change' }],
    sql_content: [{ required: true, message: '请输入 Redis 命令', trigger: 'blur' }]
  }
})

const detailDialog = reactive({
  visible: false,
  data: null
})

const approvalForm = reactive({
  comment: ''
})

// 获取 Redis 变更列表
const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize
    }
    
    // 根据 Tab 设置不同的查询参数
    if (activeTab.value === 'myRequests') {
      params.requester_id = currentUserId.value
    } else if (activeTab.value === 'pendingApproval') {
      params.status_filter = 'pending'
    } else if (activeTab.value === 'processed') {
      params.except_status = 'pending'
      params.approver_id = currentUserId.value
    }
    
    // 只显示 REDIS 类型
    params.change_type = 'REDIS'
    
    if (statusFilter.value) params.status = statusFilter.value
    
    const data = await request.get('/approvals', { params })
    approvalList.value = data.items || []
    pagination.total = data.total || 0
    
    // 更新待审批数量
    if (activeTab.value === 'pendingApproval') {
      pendingCount.value = data.total || 0
    }
  } catch (error) {
    console.error('获取列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 获取待审批数量
const fetchPendingCount = async () => {
  if (!canApprove.value) return
  try {
    const data = await request.get('/approvals', { 
      params: { status_filter: 'pending', change_type: 'REDIS', limit: 1 } 
    })
    pendingCount.value = data.total || 0
  } catch (error) {
    console.error('获取待审批数量失败:', error)
  }
}

// 获取 Redis 实例列表
const fetchRedisInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    redisInstances.value = (data.items || []).filter(inst => inst.db_type === 'redis')
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleTabChange = () => {
  pagination.page = 1
  statusFilter.value = ''
  fetchApprovals()
}

const handleAdd = () => {
  dialog.form = {
    title: '',
    instance_id: null,
    sql_content: '',
    remark: '',
    execution_mode: 'auto',  // 默认审批后自动执行
    scheduled_time: null
  }
  dialog.visible = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.submitting = true
    try {
      const submitData = {
        title: dialog.form.title,
        change_type: 'REDIS',
        instance_id: dialog.form.instance_id,
        sql_content: dialog.form.sql_content,
        remark: dialog.form.remark,
        auto_execute: dialog.form.execution_mode === 'auto'
      }
      
      if (dialog.form.execution_mode === 'scheduled' && dialog.form.scheduled_time) {
        submitData.scheduled_time = dayjs(dialog.form.scheduled_time).toISOString()
      }
      
      await request.post('/approvals', submitData)
      ElMessage.success('提交成功')
      dialog.visible = false
      fetchApprovals()
      fetchPendingCount()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '提交失败')
    } finally {
      dialog.submitting = false
    }
  })
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

const handleExecute = async (row) => {
  try {
    await ElMessageBox.confirm('确定要执行此变更吗？', '确认', { type: 'warning' })
    const result = await request.post(`/approvals/${row.id}/execute`)
    ElMessage.success(result.message || '执行成功')
    fetchApprovals()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('执行失败: ' + (error.response?.data?.detail || error.message))
    }
  }
}

const getStatusType = (status) => {
  const map = { pending: 'warning', approved: 'success', rejected: 'danger', executed: 'info', failed: 'danger' }
  return map[status] || ''
}

const getStatusLabel = (status) => {
  const map = { pending: '待审批', approved: '已通过', rejected: '已拒绝', executed: '已执行', failed: '执行失败' }
  return map[status] || status
}

const getRiskLabel = (level) => {
  const map = { critical: '极高风险', high: '高风险', medium: '中风险', low: '低风险' }
  return map[level] || level
}

const formatTime = (time) => time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'

onMounted(() => {
  fetchApprovals()
  fetchRedisInstances()
  fetchPendingCount()
})
</script>

<style lang="scss" scoped>
.redis-requests-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
    }
    
    .pending-badge {
      margin-right: 0;
    }
  }
  
  .tab-badge {
    margin-left: 5px;
  }
  
  .filter-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }
  
  .risk-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    
    &.critical { background: #fef0f0; color: #f56c6c; }
    &.high { background: #fdf6ec; color: #e6a23c; }
    &.medium { background: #f4f4f5; color: #909399; }
    &.low { background: #f0f9eb; color: #67c23a; }
  }
  
  .cmd-input-wrapper {
    width: 100%;
    
    .cmd-tips {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }
  }
  
  .cmd-preview {
    background: #f5f7fa;
    padding: 12px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 300px;
    overflow: auto;
    
    &.rollback {
      background: #fef0f0;
    }
  }
  
  .approval-actions {
    margin-top: 15px;
  }
  
  .table-operations {
    display: flex;
    flex-wrap: nowrap;
    gap: 8px;
    justify-content: center;
  }
}
</style>
