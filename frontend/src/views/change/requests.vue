<template>
  <div class="change-requests-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>变更申请</span>
            <el-tag type="info" size="small" style="margin-left: 10px;">我的申请记录</el-tag>
          </div>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            提交变更
          </el-button>
        </div>
      </template>
      
      <!-- 快速筛选 -->
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 120px;" @change="fetchApprovals">
          <el-option label="全部" value="" />
          <el-option label="待审批" value="pending" />
          <el-option label="已通过" value="approved" />
          <el-option label="已拒绝" value="rejected" />
          <el-option label="已执行" value="executed" />
        </el-select>
        <el-input v-model="searchKeyword" placeholder="搜索标题" clearable style="width: 200px;" @keyup.enter="fetchApprovals" />
        <el-button @click="fetchApprovals">刷新</el-button>
      </div>
      
      <el-table :data="approvalList" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="200">
          <template #default="{ row }">
            <div class="title-cell">
              <span class="title-text">{{ row.title }}</span>
              <el-tag v-if="row.auto_execute" type="success" size="small" style="margin-left: 6px;">自动</el-tag>
              <el-tag v-if="row.scheduled_time" type="warning" size="small" style="margin-left: 6px;">定时</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="change_type" label="类型" width="80">
          <template #default="{ row }">
            <el-tag size="small">{{ row.change_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="instance_name" label="实例" width="150" />
        <el-table-column prop="database_target" label="目标数据库" width="150">
          <template #default="{ row }">
            <span v-if="row.database_mode === 'all'">
              <el-tag type="warning" size="small">全部</el-tag>
            </span>
            <span v-else-if="row.database_mode === 'pattern'">
              <el-tag type="info" size="small">{{ row.database_pattern }}</el-tag>
            </span>
            <span v-else>{{ row.database_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sql_risk_level" label="风险" width="70">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="90">
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
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button link type="primary" @click="handleView(row)">详情</el-button>
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
    
    <!-- 提交变更对话框 - 复用原有逻辑 -->
    <el-dialog v-model="dialog.visible" title="提交变更申请" width="900px" :close-on-click-modal="false">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="110px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="标题" prop="title">
              <el-input v-model="dialog.form.title" placeholder="请输入变更标题" maxlength="100" show-word-limit />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="变更类型" prop="change_type">
              <el-select v-model="dialog.form.change_type" placeholder="请选择变更类型" style="width: 100%;">
                <el-option label="DDL变更" value="DDL" />
                <el-option label="DML变更" value="DML" />
                <el-option label="运维操作" value="OPERATION" />
                <el-option label="自定义SQL" value="CUSTOM" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="实例" prop="instance_id">
              <el-select v-model="dialog.form.instance_id" placeholder="请选择实例" style="width: 100%;" @change="handleInstanceSelect">
                <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库">
              <el-select v-model="dialog.form.database_name" placeholder="请选择数据库" style="width: 100%;" :loading="dialog.dbLoading" filterable clearable>
                <el-option v-for="db in dialog.databases" :key="db" :label="db" :value="db" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="SQL内容" prop="sql_content">
          <el-input
            v-model="dialog.form.sql_content"
            type="textarea"
            :rows="12"
            placeholder="请输入SQL语句"
            style="font-family: monospace;"
          />
        </el-form-item>
        
        <el-form-item label="备注">
          <el-input v-model="dialog.form.remark" type="textarea" :rows="2" placeholder="请输入备注信息（可选）" />
        </el-form-item>
        
        <el-form-item label="预估影响">
          <el-input-number v-model="dialog.form.affected_rows_estimate" :min="0" :max="1000000000" :step="100" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px;">预估影响的行数</span>
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
      <ApprovalDetailCard :approval="detailDialog.data" title="变更申请详情" />
      <template #footer>
        <el-button @click="detailDialog.visible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { instancesApi } from '@/api/instances'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import ApprovalDetailCard from '@/components/ApprovalDetailCard.vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)

const loading = ref(false)
const approvalList = ref([])
const instances = ref([])
const formRef = ref(null)
const statusFilter = ref('')
const searchKeyword = ref('')

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  submitting: false,
  dbLoading: false,
  databases: [],
  form: {
    title: '',
    instance_id: null,
    database_name: '',
    change_type: 'DDL',
    sql_content: '',
    remark: '',
    affected_rows_estimate: 0,
    execution_mode: 'auto',
    scheduled_time: null
  },
  rules: {
    title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
    instance_id: [{ required: true, message: '请选择实例', trigger: 'change' }],
    sql_content: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
  }
})

const detailDialog = reactive({
  visible: false,
  data: null
})

const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      requester_id: currentUserId.value
    }
    if (statusFilter.value) params.status = statusFilter.value
    
    const data = await request.get('/approvals', { params })
    approvalList.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取列表失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 100 })
    instances.value = data.items || []
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleAdd = () => {
  dialog.form = {
    title: '',
    instance_id: null,
    database_name: '',
    change_type: 'DDL',
    sql_content: '',
    remark: '',
    affected_rows_estimate: 0,
    execution_mode: 'auto',
    scheduled_time: null
  }
  dialog.visible = true
}

const handleInstanceSelect = async (instanceId) => {
  dialog.form.database_name = ''
  dialog.databases = []
  dialog.dbLoading = true
  try {
    const data = await request.get(`/sql/databases/${instanceId}`)
    const systemDbs = ['information_schema', 'mysql', 'performance_schema', 'sys', 'template0', 'template1']
    dialog.databases = data.filter(db => !systemDbs.includes(db))
  } catch (error) {
    console.error('获取数据库列表失败:', error)
  } finally {
    dialog.dbLoading = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialog.submitting = true
    try {
      const submitData = {
        title: dialog.form.title,
        change_type: dialog.form.change_type,
        instance_id: dialog.form.instance_id,
        database_name: dialog.form.database_name,
        sql_content: dialog.form.sql_content,
        remark: dialog.form.remark,
        affected_rows_estimate: dialog.form.affected_rows_estimate,
        auto_execute: dialog.form.execution_mode === 'auto'
      }
      
      if (dialog.form.execution_mode === 'scheduled' && dialog.form.scheduled_time) {
        submitData.scheduled_time = dayjs(dialog.form.scheduled_time).toISOString()
      }
      
      await request.post('/approvals', submitData)
      ElMessage.success('提交成功')
      dialog.visible = false
      fetchApprovals()
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
    detailDialog.visible = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

const handleExecute = async (row) => {
  try {
    await ElMessageBox.confirm('确定要执行此变更吗？执行后数据将无法回滚。', '警告', { type: 'warning' })
    const result = await request.post(`/approvals/${row.id}/execute`)
    ElMessage.success(result.message || '执行成功')
    fetchApprovals()
  } catch (error) {
    if (error !== 'cancel') console.error('执行失败:', error)
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
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.change-requests-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-left {
      display: flex;
      align-items: center;
    }
  }
  
  .filter-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 15px;
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
    
    .title-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
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
}
</style>
