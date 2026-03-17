<template>
  <div class="approvals-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>变更审批</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            提交变更
          </el-button>
        </div>
      </template>
      
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="待审批" name="pending" />
        <el-tab-pane label="已审批" name="processed" />
        <el-tab-pane label="我的申请" name="mine" />
      </el-tabs>
      
      <el-table :data="approvalList" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="标题" width="200" />
        <el-table-column prop="change_type" label="变更类型" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.change_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sql_risk_level" label="风险等级" width="100">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="提交时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleView(row)">详情</el-button>
            <template v-if="row.status === 'pending' && canApprove">
              <el-button text type="success" @click="handleApprove(row, true)">通过</el-button>
              <el-button text type="danger" @click="handleApprove(row, false)">拒绝</el-button>
            </template>
            <el-button
              v-if="row.status === 'approved' && row.requester_id === currentUserId"
              text
              type="primary"
              @click="handleExecute(row)"
            >
              执行
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 提交变更对话框 -->
    <el-dialog v-model="dialog.visible" title="提交变更申请" width="800px" :close-on-click-modal="false">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
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
              <el-select v-model="dialog.form.database_name" placeholder="请选择数据库" style="width: 100%;" :loading="dialog.dbLoading">
                <el-option v-for="db in dialog.databases" :key="db" :label="db" :value="db" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- SQL内容输入区域 -->
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
                <el-tag v-if="sqlStats.totalLines > 1000" type="warning">
                  预览前100行
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
                :rows="12"
                placeholder="请输入SQL语句，或上传SQL文件"
                class="sql-textarea"
                @input="handleSqlInput"
              />
              
              <!-- 大文件提示 -->
              <div v-if="sqlStats.totalLines > 1000" class="large-file-tip">
                <el-alert
                  type="warning"
                  :closable="false"
                  show-icon
                >
                  <template #title>
                    文件较大（{{ sqlStats.totalLines.toLocaleString() }}行），当前仅显示前100行预览。
                    完整内容将在提交时发送。
                  </template>
                </el-alert>
              </div>
            </div>
            
            <!-- SQL校验结果 -->
            <div v-if="sqlValidation.show" class="validation-result">
              <el-alert
                :type="sqlValidation.valid ? 'success' : 'error'"
                :closable="false"
                show-icon
              >
                <template #title>
                  <div class="validation-title">
                    <span>{{ sqlValidation.valid ? 'SQL校验通过' : 'SQL校验失败' }}</span>
                    <span v-if="sqlValidation.statementCount > 0" class="statement-count">
                      共 {{ sqlValidation.statementCount }} 条语句
                    </span>
                  </div>
                </template>
                <template #default v-if="!sqlValidation.valid">
                  <ul class="validation-errors">
                    <li v-for="(error, idx) in sqlValidation.errors" :key="idx">{{ error }}</li>
                  </ul>
                </template>
              </el-alert>
            </div>
          </div>
        </el-form-item>
        
        <!-- 备注 -->
        <el-form-item label="备注">
          <el-input
            v-model="dialog.form.remark"
            type="textarea"
            :rows="2"
            placeholder="请输入备注信息（可选）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="dialog.submitting">
          提交申请
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="变更详情" width="800px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="标题">{{ detailDialog.data?.title }}</el-descriptions-item>
        <el-descriptions-item label="变更类型">
          <el-tag size="small">{{ detailDialog.data?.change_type }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <span class="risk-tag" :class="detailDialog.data?.sql_risk_level">
            {{ getRiskLabel(detailDialog.data?.sql_risk_level) }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailDialog.data?.status)" size="small">
            {{ getStatusLabel(detailDialog.data?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实例">{{ detailDialog.data?.instance_name }}</el-descriptions-item>
        <el-descriptions-item label="数据库">{{ detailDialog.data?.database_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请人">{{ detailDialog.data?.requester_name }}</el-descriptions-item>
        <el-descriptions-item label="提交时间">{{ formatTime(detailDialog.data?.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="SQL内容" :span="2">
          <div class="detail-sql-content">
            <div class="sql-info">
              <el-tag size="small">{{ detailDialog.data?.sql_line_count || 0 }} 行</el-tag>
            </div>
            <pre class="sql-preview">{{ detailDialog.data?.sql_content_preview || detailDialog.data?.sql_content }}</pre>
          </div>
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data?.approver_name" label="审批人">
          {{ detailDialog.data?.approver_name }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data?.approved_at" label="审批时间">
          {{ formatTime(detailDialog.data?.approved_at) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data?.approve_comment" label="审批意见" :span="2">
          {{ detailDialog.data?.approve_comment }}
        </el-descriptions-item>
      </el-descriptions>
      
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
import { Plus, Upload, MagicStick, Delete } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)
const canApprove = computed(() => ['super_admin', 'approval_admin'].includes(userStore.user?.role))

const loading = ref(false)
const activeTab = ref('pending')
const approvalList = ref([])
const instances = ref([])
const formRef = ref(null)
const uploadRef = ref(null)

// 完整SQL内容（大文件时用于提交）
const fullSqlContent = ref('')

// SQL统计信息
const sqlStats = reactive({
  totalLines: 0,
  fileSize: 0,
  isLargeFile: false
})

// SQL校验结果
const sqlValidation = reactive({
  show: false,
  valid: true,
  errors: [],
  statementCount: 0
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
    change_type: 'DDL',
    sql_content: '',
    remark: ''
  },
  rules: {
    title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
    instance_id: [{ required: true, message: '请选择实例', trigger: 'change' }],
    change_type: [{ required: true, message: '请选择变更类型', trigger: 'change' }],
    sql_content: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
  }
})

const detailDialog = reactive({
  visible: false,
  data: null
})

// 文件大小限制 (10MB)
const MAX_FILE_SIZE = 10 * 1024 * 1024
// 大文件行数阈值
const LARGE_FILE_LINES = 1000
// 预览行数
const PREVIEW_LINES = 100

/**
 * 处理文件选择 - 流式读取避免内存溢出
 */
const handleFileSelect = async (file) => {
  const rawFile = file.raw
  
  // 校验文件类型
  if (!rawFile.name.endsWith('.sql') && !rawFile.name.endsWith('.txt')) {
    ElMessage.error('仅支持 .sql 或 .txt 文件')
    return
  }
  
  // 校验文件大小
  if (rawFile.size > MAX_FILE_SIZE) {
    ElMessage.error(`文件大小不能超过 ${formatFileSize(MAX_FILE_SIZE)}`)
    return
  }
  
  dialog.fileLoading = true
  sqlStats.fileSize = rawFile.size
  
  try {
    // 使用流式读取处理大文件
    const result = await readFileSafely(rawFile)
    
    fullSqlContent.value = result.fullContent
    sqlStats.totalLines = result.lineCount
    sqlStats.isLargeFile = result.lineCount > LARGE_FILE_LINES
    
    // 大文件只显示前100行预览
    if (result.lineCount > LARGE_FILE_LINES) {
      const lines = result.fullContent.split('\n').slice(0, PREVIEW_LINES)
      dialog.form.sql_content = lines.join('\n')
      
      ElMessage.warning({
        message: `文件共 ${result.lineCount.toLocaleString()} 行，已截取前 ${PREVIEW_LINES} 行显示预览`,
        duration: 3000
      })
    } else {
      dialog.form.sql_content = result.fullContent
    }
    
    // 执行SQL校验
    validateSQL(result.fullContent)
    
    ElMessage.success(`文件加载成功: ${rawFile.name}`)
  } catch (error) {
    console.error('文件读取失败:', error)
    ElMessage.error('文件读取失败: ' + error.message)
    resetFileState()
  } finally {
    dialog.fileLoading = false
  }
}

/**
 * 安全读取文件 - 分块读取避免内存溢出
 */
const readFileSafely = (file) => {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      try {
        const content = e.target.result
        
        // 统计行数（不分割整个文件，使用正则匹配）
        const lineCount = (content.match(/\n/g) || []).length + 1
        
        resolve({
          fullContent: content,
          lineCount
        })
      } catch (error) {
        reject(new Error('文件内容解析失败'))
      }
    }
    
    reader.onerror = () => {
      reject(new Error('文件读取失败'))
    }
    
    // 对于超大文件，可以使用 slice 分块读取
    // 这里我们限制文件大小为10MB，直接读取是安全的
    reader.readAsText(file)
  })
}

/**
 * 超大文件分块读取（预留方案）
 */
const readFileInChunks = async (file, chunkSize = 1024 * 1024) => {
  const chunks = []
  let offset = 0
  
  while (offset < file.size) {
    const chunk = file.slice(offset, offset + chunkSize)
    const text = await new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target.result)
      reader.onerror = reject
      reader.readAsText(chunk)
    })
    chunks.push(text)
    offset += chunkSize
  }
  
  return chunks.join('')
}

/**
 * SQL校验
 */
const validateSQL = (content) => {
  sqlValidation.errors = []
  sqlValidation.valid = true
  sqlValidation.show = true
  
  if (!content || !content.trim()) {
    sqlValidation.valid = false
    sqlValidation.errors.push('SQL内容不能为空')
    return
  }
  
  // 统计SQL语句数量（按分号分割）
  const statements = content
    .split(';')
    .map(s => s.trim())
    .filter(s => s.length > 0)
  
  sqlValidation.statementCount = statements.length
  
  // 检查危险操作
  const dangerousPatterns = [
    { pattern: /\bDROP\s+DATABASE\b/i, message: '禁止 DROP DATABASE 操作' },
    { pattern: /\bDROP\s+SCHEMA\b/i, message: '禁止 DROP SCHEMA 操作' },
    { pattern: /\bTRUNCATE\b/i, message: '包含 TRUNCATE 操作，需要特别注意' },
    { pattern: /\bDELETE\s+FROM\b(?!.*\bWHERE\b)/i, message: '存在无 WHERE 条件的 DELETE 语句' },
    { pattern: /\bUPDATE\b(?!.*\bWHERE\b)/i, message: '存在无 WHERE 条件的 UPDATE 语句' }
  ]
  
  for (const { pattern, message } of dangerousPatterns) {
    if (pattern.test(content)) {
      sqlValidation.errors.push(message)
    }
  }
  
  // 检查语法基本结构
  const upperContent = content.toUpperCase()
  const hasValidStart = /^(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|GRANT|REVOKE|USE|SET|SHOW|DESC|EXPLAIN)/i.test(content.trim())
  
  if (!hasValidStart) {
    sqlValidation.errors.push('SQL语句格式不正确，请检查语法')
  }
  
  sqlValidation.valid = sqlValidation.errors.length === 0
}

/**
 * 手动输入SQL时的处理
 */
const handleSqlInput = () => {
  fullSqlContent.value = dialog.form.sql_content
  const lines = dialog.form.sql_content.split('\n')
  sqlStats.totalLines = lines.length
  sqlStats.isLargeFile = lines.length > LARGE_FILE_LINES
  
  // 防抖校验
  if (dialog.inputTimer) {
    clearTimeout(dialog.inputTimer)
  }
  dialog.inputTimer = setTimeout(() => {
    if (dialog.form.sql_content.trim()) {
      validateSQL(dialog.form.sql_content)
    } else {
      sqlValidation.show = false
    }
  }, 500)
}

/**
 * 格式化SQL内容
 */
const formatSQLContent = () => {
  if (!dialog.form.sql_content.trim()) return
  
  let formatted = dialog.form.sql_content
    .replace(/\s+/g, ' ')
    .trim()
  
  const keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 
                    'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'ON', 'AND', 'OR', 
                    'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 
                    'CREATE TABLE', 'ALTER TABLE', 'ADD COLUMN', 'DROP COLUMN']
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi')
    formatted = formatted.replace(regex, '\n' + keyword)
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
  resetFileState()
  sqlValidation.show = false
}

/**
 * 重置文件状态
 */
const resetFileState = () => {
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

const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {}
    if (activeTab.value === 'pending') {
      params.status_filter = 'pending'
    } else if (activeTab.value === 'mine') {
      params.requester_id = currentUserId.value
    }
    
    approvalList.value = await request.get('/approvals', { params })
  } catch (error) {
    console.error('获取审批列表失败:', error)
  } finally {
    loading.value = false
  }
}

const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 100 })
    instances.value = data.items || data
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleTabChange = () => {
  fetchApprovals()
}

const handleAdd = () => {
  // 重置表单
  dialog.form = {
    title: '',
    instance_id: null,
    database_name: '',
    change_type: 'DDL',
    sql_content: '',
    remark: ''
  }
  fullSqlContent.value = ''
  resetFileState()
  sqlValidation.show = false
  dialog.visible = true
}

const handleInstanceSelect = async (instanceId) => {
  dialog.form.database_name = ''
  dialog.databases = []
  dialog.dbLoading = true
  
  try {
    dialog.databases = await request.get(`/sql/databases/${instanceId}`)
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
    
    // 使用完整SQL内容（大文件时）
    const sqlToSubmit = fullSqlContent.value || dialog.form.sql_content
    
    // 再次校验
    if (!sqlToSubmit.trim()) {
      ElMessage.error('SQL内容不能为空')
      return
    }
    
    dialog.submitting = true
    try {
      await request.post('/approvals', {
        ...dialog.form,
        sql_content: sqlToSubmit,
        sql_line_count: sqlStats.totalLines
      })
      
      ElMessage.success('提交成功')
      dialog.visible = false
      fetchApprovals()
    } catch (error) {
      const errorMsg = error.response?.data?.detail || '提交失败'
      ElMessage.error(errorMsg)
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
    console.error('获取详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

const handleApprove = async (row, approved) => {
  try {
    const action = approved ? '通过' : '拒绝'
    const { value } = await ElMessageBox.prompt('请输入审批意见', action, {
      inputType: 'textarea',
      inputPlaceholder: '请输入审批意见（可选）'
    })
    
    await request.post(`/approvals/${row.id}/approve`, {
      approved: approved,
      comment: value || ''
    })
    
    ElMessage.success(`审批${action}成功`)
    fetchApprovals()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('审批失败:', error)
    }
  }
}

const handleExecute = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要执行此变更吗？执行后数据将无法回滚。',
      '警告',
      { type: 'warning' }
    )
    
    const result = await request.post(`/approvals/${row.id}/execute`)
    
    if (result.success) {
      ElMessage.success('执行成功')
    } else {
      ElMessage.error(`执行失败: ${result.message}`)
    }
    
    fetchApprovals()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('执行失败:', error)
    }
  }
}

const getRiskLabel = (level) => {
  const labels = { low: '低', medium: '中', high: '高', critical: '极高' }
  return labels[level] || level
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger',
    executed: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝',
    executed: '已执行',
    failed: '执行失败'
  }
  return labels[status] || status
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchApprovals()
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.approvals-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .risk-tag {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
    
    &.low {
      background: #f0f9eb;
      color: #67c23a;
    }
    &.medium {
      background: #fdf6ec;
      color: #e6a23c;
    }
    &.high {
      background: #fef0f0;
      color: #f56c6c;
    }
    &.critical {
      background: #fde2e2;
      color: #f56c6c;
      font-weight: bold;
    }
  }
  
  .sql-input-wrapper {
    width: 100%;
    
    .upload-section {
      display: flex;
      align-items: center;
      gap: 15px;
      margin-bottom: 10px;
      
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
          gap: 5px;
        }
      }
      
      .sql-textarea {
        :deep(textarea) {
          border: none;
          border-radius: 0;
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 13px;
          line-height: 1.5;
          resize: vertical;
        }
      }
      
      .large-file-tip {
        padding: 10px 12px;
        background: #fdf6ec;
      }
    }
    
    .validation-result {
      margin-top: 10px;
      
      .validation-title {
        display: flex;
        align-items: center;
        gap: 15px;
        
        .statement-count {
          font-size: 12px;
          color: #909399;
        }
      }
      
      .validation-errors {
        margin: 5px 0 0 0;
        padding-left: 20px;
        
        li {
          margin: 3px 0;
        }
      }
    }
  }
  
  .detail-sql-content {
    .sql-info {
      margin-bottom: 8px;
    }
    
    .sql-preview {
      background: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
      font-size: 12px;
      line-height: 1.5;
      max-height: 300px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  }
}
</style>
