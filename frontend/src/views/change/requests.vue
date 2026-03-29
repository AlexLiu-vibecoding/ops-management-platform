<template>
  <div class="change-requests-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div class="header-left">
            <span>DB 变更</span>
            <el-tag type="info" size="small" style="margin-left: 10px;">MySQL / PostgreSQL</el-tag>
          </div>
          <div class="header-right">
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              提交变更
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
        <el-input v-model="searchKeyword" placeholder="搜索标题" clearable style="width: 200px;" @keyup.enter="fetchApprovals" />
        <el-button @click="fetchApprovals">刷新</el-button>
      </div>
      
      <el-table :data="approvalList" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="title-cell">
              <span class="title-text">{{ row.title }}</span>
              <el-tag v-if="row.auto_execute" type="success" size="small" style="margin-left: 6px;">自动</el-tag>
              <el-tag v-if="row.scheduled_time" type="warning" size="small" style="margin-left: 6px;">定时</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="change_type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.change_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="instance_name" label="实例" min-width="120" show-overflow-tooltip />
        <el-table-column prop="database_target" label="目标" min-width="100" show-overflow-tooltip>
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
        <el-table-column prop="sql_risk_level" label="风险" width="60" align="center">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
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
        <el-table-column label="操作" width="140" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions 
              :row="row" 
              :actions="getChangeActions(row)"
              :max-primary="2"
              @view="handleView"
              @approve="handleApprove($event, true)"
              @reject="handleApprove($event, false)"
              @execute="handleExecute"
            />
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
                <el-option v-for="inst in dbInstances" :key="inst.id" :label="`${inst.name} (${inst.db_type || 'mysql'})`" :value="inst.id" />
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
          <div class="sql-input-wrapper">
            <!-- 文件上传区域 -->
            <div class="upload-section">
              <el-upload
                ref="uploadRef"
                :auto-upload="false"
                :show-file-list="false"
                accept=".sql,.txt"
                :on-change="handleFileSelect"
                :disabled="dialog.fileLoading"
              >
                <el-button type="primary" plain :loading="dialog.fileLoading">
                  <el-icon><Upload /></el-icon>
                  {{ dialog.fileLoading ? '正在读取文件...' : '上传SQL文件' }}
                </el-button>
              </el-upload>
              
              <!-- SQL统计信息 -->
              <div v-if="sqlStats.totalLines > 0" class="sql-stats">
                <el-tag :type="sqlStats.totalLines > 1000 ? 'warning' : 'success'">
                  共 {{ sqlStats.totalLines.toLocaleString() }} 行
                </el-tag>
                <el-tag type="info">
                  {{ formatFileSize(sqlStats.fileSize) }}
                </el-tag>
              </div>
            </div>
            
            <!-- SQL内容编辑器 -->
            <div class="editor-container">
              <div class="editor-header">
                <span>SQL内容</span>
                <div class="editor-actions">
                  <el-button size="small" text @click="formatSQLContent">
                    <el-icon><MagicStick /></el-icon>
                    格式化
                  </el-button>
                  <el-button size="small" text @click="clearSQLContent">
                    <el-icon><Delete /></el-icon>
                    清空
                  </el-button>
                </div>
              </div>
              
              <el-input
                v-model="dialog.form.sql_content"
                type="textarea"
                :rows="10"
                placeholder="请输入SQL语句，或上传SQL文件"
                class="sql-textarea"
                style="font-family: monospace;"
              />
            </div>
          </div>
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
    <el-dialog v-model="detailDialog.visible" title="变更详情" width="900px">
      <ApprovalDetailCard :approval="detailDialog.data" title="变更申请详情" />
      
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
import { instancesApi } from '@/api/instances'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, MagicStick, Delete, View, CircleCheck, CircleClose, VideoPlay } from '@element-plus/icons-vue'
import ApprovalDetailCard from '@/components/ApprovalDetailCard.vue'
import TableActions from '@/components/TableActions.vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)
const userRole = computed(() => userStore.user?.role)

// 是否有审批权限
const canApprove = computed(() => ['super_admin', 'approval_admin'].includes(userRole.value))

// 获取变更操作配置
const getChangeActions = (row) => {
  const actions = [
    { 
      key: 'view', 
      label: '详情', 
      event: 'view', 
      primary: true,
      icon: View
    }
  ]
  
  // 待审批状态：审批人可操作
  if (row.status === 'pending' && canApprove.value) {
    actions.push({ 
      key: 'approve', 
      label: '通过', 
      event: 'approve', 
      primary: true,
      icon: CircleCheck
    })
    actions.push({ 
      key: 'reject', 
      label: '拒绝', 
      event: 'reject', 
      danger: true,
      icon: CircleClose
    })
  }
  
  // 已通过且非自动执行：可手动执行
  if (row.status === 'approved' && !row.auto_execute && !row.scheduled_time) {
    actions.push({ 
      key: 'execute', 
      label: '执行', 
      event: 'execute', 
      icon: VideoPlay
    })
  }
  
  return actions
}

const loading = ref(false)
const approvalList = ref([])
const instances = ref([])
const formRef = ref(null)
const uploadRef = ref(null)
const statusFilter = ref('')
const searchKeyword = ref('')
const activeTab = ref('myRequests')
const pendingCount = ref(0)

// 完整SQL内容（大文件时用于提交）
const fullSqlContent = ref('')

// SQL统计信息
const sqlStats = reactive({
  totalLines: 0,
  fileSize: 0,
  isLargeFile: false
})

// 文件大小限制
const MAX_FILE_SIZE = 10 * 1024 * 1024

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 过滤出 DB 实例（非 Redis）
const dbInstances = computed(() => {
  return instances.value.filter(inst => inst.db_type !== 'redis')
})

const dialog = reactive({
  visible: false,
  submitting: false,
  fileLoading: false,
  dbLoading: false,
  databases: [],
  form: {
    title: '',
    instance_id: null,
    database_name: '',
    change_type: 'DML',  // 默认 DML
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

const approvalForm = reactive({
  comment: ''
})

const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {
      skip: (pagination.page - 1) * pagination.pageSize,
      limit: pagination.pageSize,
      exclude_change_type: 'REDIS'  // 所有 Tab 都排除 REDIS 类型
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

const fetchPendingCount = async () => {
  if (!canApprove.value) return
  try {
    const data = await request.get('/approvals', { 
      params: { status_filter: 'pending', exclude_change_type: 'REDIS', limit: 1 } 
    })
    pendingCount.value = data.total || 0
  } catch (error) {
    console.error('获取待审批数量失败:', error)
  }
}

const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 100 })
    // 过滤掉 Redis 实例，只显示 MySQL/PostgreSQL
    instances.value = (data.items || []).filter(i => i.db_type !== 'redis')
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
    database_name: '',
    change_type: 'DML',  // 默认 DML
    sql_content: '',
    remark: '',
    affected_rows_estimate: 0,
    execution_mode: 'auto',
    scheduled_time: null
  }
  // 重置文件状态
  fullSqlContent.value = ''
  sqlStats.totalLines = 0
  sqlStats.fileSize = 0
  sqlStats.isLargeFile = false
  dialog.visible = true
}

/**
 * 处理文件选择
 */
const handleFileSelect = async (file) => {
  const rawFile = file.raw
  
  if (!rawFile.name.endsWith('.sql') && !rawFile.name.endsWith('.txt')) {
    ElMessage.error('仅支持 .sql 或 .txt 文件')
    return
  }
  
  if (rawFile.size > MAX_FILE_SIZE) {
    ElMessage.error(`文件大小不能超过 ${formatFileSize(MAX_FILE_SIZE)}`)
    return
  }
  
  dialog.fileLoading = true
  sqlStats.fileSize = rawFile.size
  
  try {
    const reader = new FileReader()
    reader.onload = (e) => {
      const content = e.target.result
      fullSqlContent.value = content
      
      const lineCount = (content.match(/\n/g) || []).length + 1
      sqlStats.totalLines = lineCount
      sqlStats.isLargeFile = lineCount > 1000
      
      if (lineCount > 100) {
        const lines = content.split('\n').slice(0, 100)
        dialog.form.sql_content = lines.join('\n')
        ElMessage.warning(`文件共 ${lineCount.toLocaleString()} 行，已截取前100行显示预览`)
      } else {
        dialog.form.sql_content = content
      }
      
      ElMessage.success(`文件加载成功: ${rawFile.name}`)
    }
    reader.readAsText(rawFile)
  } catch (error) {
    ElMessage.error('文件读取失败: ' + error.message)
    resetFileState()
  } finally {
    dialog.fileLoading = false
  }
}

/**
 * 重置文件状态
 */
const resetFileState = () => {
  fullSqlContent.value = ''
  sqlStats.totalLines = 0
  sqlStats.fileSize = 0
  sqlStats.isLargeFile = false
}

/**
 * 格式化SQL内容
 */
const formatSQLContent = () => {
  if (!dialog.form.sql_content.trim()) return
  let formatted = dialog.form.sql_content.replace(/\s+/g, ' ').trim()
  const keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY', 'LIMIT', 'JOIN', 'ON', 'AND', 'OR']
  keywords.forEach(kw => {
    formatted = formatted.replace(new RegExp(`\\b${kw}\\b`, 'gi'), '\n' + kw)
  })
  dialog.form.sql_content = formatted.trim()
  fullSqlContent.value = dialog.form.sql_content
  ElMessage.success('SQL已格式化')
}

/**
 * 清空SQL内容
 */
const clearSQLContent = () => {
  dialog.form.sql_content = ''
  fullSqlContent.value = ''
  sqlStats.totalLines = 0
  sqlStats.fileSize = 0
  sqlStats.isLargeFile = false
}

/**
 * 格式化文件大小
 */
const formatFileSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handleInstanceSelect = async (instanceId) => {
  dialog.form.database_name = ''
  dialog.databases = []
  
  // 获取数据库列表
  dialog.dbLoading = true
  try {
    const data = await request.get(`/sql/databases/${instanceId}`)
    const systemDbs = ['information_schema', 'mysql', 'performance_schema', 'sys', 'template0', 'template1']
    dialog.databases = data.filter(db => !systemDbs.includes(db))
  } catch (error) {
    console.error('获取数据库列表失败:', error)
    ElMessage.warning('获取数据库列表失败，请手动输入数据库名')
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
      // 如果是大文件，使用完整内容提交
      const sqlToSubmit = fullSqlContent.value || dialog.form.sql_content
      
      const submitData = {
        title: dialog.form.title,
        change_type: dialog.form.change_type,
        instance_id: dialog.form.instance_id,
        database_name: dialog.form.database_name,
        sql_content: sqlToSubmit,
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
  fetchPendingCount()
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
  
  .tab-badge {
    margin-left: 5px;
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
  
  .sql-input-wrapper {
    width: 100%;
    
    .upload-section {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 12px;
      
      .sql-stats {
        display: flex;
        gap: 8px;
      }
    }
    
    .editor-container {
      border: 1px solid #dcdfe6;
      border-radius: 4px;
      overflow: hidden;
      
      .editor-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 12px;
        background: #f5f7fa;
        border-bottom: 1px solid #dcdfe6;
        
        span {
          font-weight: 500;
          color: #606266;
        }
        
        .editor-actions {
          display: flex;
          gap: 8px;
        }
      }
      
      .sql-textarea {
        :deep(.el-textarea__inner) {
          border: none;
          border-radius: 0;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 13px;
          line-height: 1.5;
        }
      }
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
  
  .approval-actions {
    margin-top: 15px;
  }
}
</style>
