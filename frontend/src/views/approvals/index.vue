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
        <el-table-column prop="database_target" label="目标数据库" width="200">
          <template #default="{ row }">
            <span v-if="row.database_mode === 'all'">
              <el-tag type="warning">全部数据库</el-tag>
            </span>
            <span v-else-if="row.database_mode === 'pattern'">
              <el-tag type="info">{{ row.database_pattern || '通配符匹配' }}</el-tag>
            </span>
            <span v-else-if="row.database_mode === 'auto'">
              <el-tag type="success">SQL自动解析</el-tag>
            </span>
            <span v-else>{{ row.database_name || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="sql_risk_level" label="风险等级" width="80">
          <template #default="{ row }">
            <span class="risk-tag" :class="row.sql_risk_level">{{ getRiskLabel(row.sql_risk_level) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="affected_rows_estimate" label="预估影响" width="100">
          <template #default="{ row }">
            <span v-if="row.affected_rows_estimate">{{ row.affected_rows_estimate.toLocaleString() }} 行</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
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
        <el-table-column label="操作" width="180" fixed="right">
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
            <el-form-item label="数据库选择模式">
              <el-select v-model="dialog.form.database_mode" placeholder="选择模式" style="width: 100%;" @change="handleDatabaseModeChange">
                <el-option label="单库选择" value="single" />
                <el-option label="多库选择" value="multiple" />
                <el-option label="通配符匹配" value="pattern" />
                <el-option label="全部数据库" value="all" />
                <el-option label="SQL自动解析" value="auto" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 单库选择 -->
        <el-form-item v-if="dialog.form.database_mode === 'single'" label="数据库">
          <el-select v-model="dialog.form.database_name" placeholder="请选择数据库" style="width: 100%;" :loading="dialog.dbLoading" filterable>
            <el-option v-for="db in dialog.databases" :key="db" :label="db" :value="db" />
          </el-select>
        </el-form-item>
        
        <!-- 多库选择 -->
        <el-form-item v-if="dialog.form.database_mode === 'multiple'" label="数据库">
          <el-select
            v-model="dialog.form.database_list"
            multiple
            collapse-tags
            collapse-tags-tooltip
            placeholder="请选择多个数据库"
            style="width: 100%;"
            :loading="dialog.dbLoading"
            filterable
          >
            <el-option v-for="db in dialog.databases" :key="db" :label="db" :value="db" />
          </el-select>
          <div class="selected-count">已选择 {{ dialog.form.database_list?.length || 0 }} 个数据库</div>
        </el-form-item>
        
        <!-- 通配符匹配 -->
        <el-form-item v-if="dialog.form.database_mode === 'pattern'" label="数据库匹配">
          <div class="pattern-input-wrapper">
            <el-input
              v-model="dialog.form.database_pattern"
              placeholder="输入通配符，如: db_% 或 user_db_*"
              @input="handlePatternChange"
            >
              <template #append>
                <el-button @click="previewPatternMatch" :loading="dialog.patternLoading">
                  预览匹配
                </el-button>
              </template>
            </el-input>
          </div>
          <div v-if="dialog.matchedDatabases.length > 0" class="matched-databases">
            <div class="matched-header">
              <span>匹配到 {{ dialog.matchedDatabases.length }} 个数据库</span>
              <el-button type="primary" link size="small" @click="showAllMatched = !showAllMatched">
                {{ showAllMatched ? '收起' : '展开全部' }}
              </el-button>
            </div>
            <div class="matched-list">
              <el-tag
                v-for="(db, idx) in displayMatchedDatabases"
                :key="db"
                size="small"
                style="margin: 2px;"
              >
                {{ db }}
              </el-tag>
              <span v-if="!showAllMatched && dialog.matchedDatabases.length > 20">
                ... 等 {{ dialog.matchedDatabases.length }} 个
              </span>
            </div>
          </div>
        </el-form-item>
        
        <!-- 全部数据库 -->
        <el-form-item v-if="dialog.form.database_mode === 'all'" label="数据库范围">
          <el-alert type="warning" :closable="false" show-icon>
            <template #title>
              将对实例上的所有数据库执行此变更
            </template>
          </el-alert>
          <div class="db-count-info" v-if="dialog.databases.length > 0">
            当前实例共有 <strong>{{ dialog.databases.length }}</strong> 个数据库
            <el-button type="primary" link size="small" @click="showDbList = true">查看列表</el-button>
          </div>
        </el-form-item>
        
        <!-- SQL自动解析 -->
        <el-form-item v-if="dialog.form.database_mode === 'auto'" label="数据库">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>
              系统将自动解析SQL中引用的数据库（如 db_001.table_name）
            </template>
          </el-alert>
          <div v-if="parsedDatabases.length > 0" class="parsed-databases">
            <span>从SQL解析到 {{ parsedDatabases.length }} 个数据库：</span>
            <el-tag v-for="db in parsedDatabases.slice(0, 10)" :key="db" size="small" style="margin: 2px;">
              {{ db }}
            </el-tag>
            <span v-if="parsedDatabases.length > 10">... 等 {{ parsedDatabases.length }} 个</span>
          </div>
        </el-form-item>
        
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
                @input="handleSqlInput"
              />
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
        
        <!-- 预估影响行数 -->
        <el-form-item label="预估影响行数">
          <el-input-number
            v-model="dialog.form.affected_rows_estimate"
            :min="0"
            :max="1000000000"
            :step="100"
            placeholder="预估影响的行数"
            style="width: 200px;"
          />
          <span class="form-tip" style="margin-left: 10px;">
            <el-icon><InfoFilled /></el-icon>
            用于评估变更影响范围，会显示在通知中
          </span>
        </el-form-item>
        
        <!-- 执行方式 -->
        <el-form-item label="执行方式">
          <div class="execution-mode-wrapper">
            <el-radio-group v-model="dialog.form.execution_mode" @change="handleExecutionModeChange">
              <el-radio value="manual">手动执行</el-radio>
              <el-radio value="auto">审批后自动执行</el-radio>
              <el-radio value="scheduled">定时执行</el-radio>
            </el-radio-group>
          </div>
          <div v-if="dialog.form.execution_mode === 'auto'" class="execution-tip">
            <el-alert type="warning" :closable="false" show-icon>
              审批通过后将立即自动执行SQL变更，请确认风险
            </el-alert>
          </div>
          <div v-if="dialog.form.execution_mode === 'scheduled'" class="scheduled-time-picker">
            <el-date-picker
              v-model="dialog.form.scheduled_time"
              type="datetime"
              placeholder="选择执行时间"
              :disabled-date="disabledDate"
              style="width: 240px;"
            />
            <el-tag type="warning" size="small" style="margin-left: 10px;">
              将在指定时间自动执行
            </el-tag>
          </div>
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
        <el-descriptions-item label="预估影响行数">
          <span v-if="detailDialog.data?.affected_rows_estimate">
            {{ detailDialog.data?.affected_rows_estimate.toLocaleString() }} 行
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="实际影响行数">
          <span v-if="detailDialog.data?.affected_rows_actual">
            {{ detailDialog.data?.affected_rows_actual.toLocaleString() }} 行
          </span>
          <span v-else>-</span>
        </el-descriptions-item>
        <el-descriptions-item label="执行方式">
          <template v-if="detailDialog.data?.scheduled_time">
            <el-tag type="warning" size="small">
              定时执行: {{ formatTime(detailDialog.data?.scheduled_time) }}
            </el-tag>
          </template>
          <template v-else-if="detailDialog.data?.auto_execute">
            <el-tag type="success" size="small">⚡ 审批后自动执行</el-tag>
          </template>
          <template v-else>
            <el-tag type="info" size="small">手动执行</el-tag>
          </template>
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailDialog.data?.status)" size="small">
            {{ getStatusLabel(detailDialog.data?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="实例">{{ detailDialog.data?.instance_name }}</el-descriptions-item>
        <el-descriptions-item label="数据库">
          <template v-if="detailDialog.data?.database_mode === 'all'">
            <el-tag type="warning">全部数据库</el-tag>
          </template>
          <template v-else-if="detailDialog.data?.database_mode === 'pattern'">
            <el-tag type="info">{{ detailDialog.data?.database_pattern }}</el-tag>
            <span v-if="detailDialog.data?.matched_database_count">
              ({{ detailDialog.data?.matched_database_count }} 个)
            </span>
          </template>
          <template v-else-if="detailDialog.data?.database_mode === 'multiple'">
            <el-tag>{{ detailDialog.data?.database_list?.length || 0 }} 个数据库</el-tag>
          </template>
          <template v-else>{{ detailDialog.data?.database_name || '-' }}</template>
        </el-descriptions-item>
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
    
    <!-- 数据库列表弹窗 -->
    <el-dialog v-model="showDbList" title="数据库列表" width="500px">
      <el-input v-model="dbSearchFilter" placeholder="搜索数据库" style="margin-bottom: 10px;" />
      <div class="db-list-container">
        <el-tag v-for="db in filteredDatabases" :key="db" size="small" style="margin: 2px;">
          {{ db }}
        </el-tag>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '@/api/index'
import { instancesApi } from '@/api/instances'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, MagicStick, Delete, InfoFilled } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const userStore = useUserStore()
const route = useRoute()
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
const showAllMatched = ref(false)
const showDbList = ref(false)
const dbSearchFilter = ref('')

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

// 从SQL解析的数据库
const parsedDatabases = ref([])

const dialog = reactive({
  visible: false,
  submitting: false,
  fileLoading: false,
  dbLoading: false,
  patternLoading: false,
  databases: [],
  matchedDatabases: [],
  form: {
    title: '',
    instance_id: null,
    database_mode: 'single',
    database_name: '',
    database_list: [],
    database_pattern: '',
    change_type: 'DDL',
    sql_content: '',
    remark: '',
    affected_rows_estimate: 0,
    execution_mode: 'auto', // manual, auto, scheduled - 默认审批后自动执行
    scheduled_time: null
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

// 显示的匹配数据库（限制数量）
const displayMatchedDatabases = computed(() => {
  if (showAllMatched.value) {
    return dialog.matchedDatabases
  }
  return dialog.matchedDatabases.slice(0, 20)
})

// 过滤后的数据库列表
const filteredDatabases = computed(() => {
  if (!dbSearchFilter.value) return dialog.databases
  return dialog.databases.filter(db => 
    db.toLowerCase().includes(dbSearchFilter.value.toLowerCase())
  )
})

// 文件大小限制
const MAX_FILE_SIZE = 10 * 1024 * 1024

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
      
      // 解析SQL中的数据库引用
      parseSqlDatabases(content)
      validateSQL(content)
      
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
 * 解析SQL中的数据库引用
 */
const parseSqlDatabases = (content) => {
  // 匹配 database.table 格式
  const dbTablePattern = /(?:FROM|JOIN|INTO|UPDATE|TABLE)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\./gi
  const matches = content.matchAll(dbTablePattern)
  const dbs = new Set()
  
  for (const match of matches) {
    const dbName = match[1]
    // 过滤系统保留字
    const reservedWords = ['select', 'insert', 'update', 'delete', 'from', 'where', 'and', 'or']
    if (!reservedWords.includes(dbName.toLowerCase())) {
      dbs.add(dbName)
    }
  }
  
  parsedDatabases.value = Array.from(dbs)
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
  
  const statements = content.split(';').filter(s => s.trim().length > 0)
  sqlValidation.statementCount = statements.length
  
  const dangerousPatterns = [
    { pattern: /\bDROP\s+DATABASE\b/i, message: '禁止 DROP DATABASE 操作' },
    { pattern: /\bDROP\s+SCHEMA\b/i, message: '禁止 DROP SCHEMA 操作' },
    { pattern: /\bTRUNCATE\b/i, message: '包含 TRUNCATE 操作，需要特别注意' }
  ]
  
  for (const { pattern, message } of dangerousPatterns) {
    if (pattern.test(content)) {
      sqlValidation.errors.push(message)
    }
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
  
  parseSqlDatabases(dialog.form.sql_content)
  
  if (dialog.inputTimer) clearTimeout(dialog.inputTimer)
  dialog.inputTimer = setTimeout(() => {
    if (dialog.form.sql_content.trim()) {
      validateSQL(dialog.form.sql_content)
    } else {
      sqlValidation.show = false
    }
  }, 500)
}

/**
 * 格式化SQL
 */
const formatSQLContent = () => {
  if (!dialog.form.sql_content.trim()) return
  // 简单格式化
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
  resetFileState()
  sqlValidation.show = false
  parsedDatabases.value = []
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

/**
 * 处理实例选择
 */
const handleInstanceSelect = async (instanceId) => {
  dialog.form.database_name = ''
  dialog.form.database_list = []
  dialog.form.database_pattern = ''
  dialog.matchedDatabases = []
  dialog.databases = []
  dialog.dbLoading = true
  
  try {
    const data = await request.get(`/sql/databases/${instanceId}`)
    // 过滤系统库
    const systemDbs = ['information_schema', 'mysql', 'performance_schema', 'sys', 'template0', 'template1', '_supabase']
    dialog.databases = data.filter(db => !systemDbs.includes(db))
  } catch (error) {
    console.error('获取数据库列表失败:', error)
  } finally {
    dialog.dbLoading = false
  }
}

/**
 * 处理数据库模式变更
 */
const handleDatabaseModeChange = () => {
  dialog.form.database_name = ''
  dialog.form.database_list = []
  dialog.form.database_pattern = ''
  dialog.matchedDatabases = []
}

/**
 * 处理通配符输入变化
 */
const handlePatternChange = () => {
  dialog.matchedDatabases = []
}

/**
 * 预览通配符匹配
 */
const previewPatternMatch = () => {
  if (!dialog.form.database_pattern) {
    ElMessage.warning('请输入匹配模式')
    return
  }
  
  dialog.patternLoading = true
  
  // 将SQL通配符转换为正则
  let pattern = dialog.form.database_pattern
    .replace(/%/g, '.*')
    .replace(/_/g, '.')
    .replace(/\*/g, '.*')
  
  try {
    const regex = new RegExp(`^${pattern}$`, 'i')
    dialog.matchedDatabases = dialog.databases.filter(db => regex.test(db))
    ElMessage.success(`匹配到 ${dialog.matchedDatabases.length} 个数据库`)
  } catch (error) {
    ElMessage.error('匹配模式无效')
    dialog.matchedDatabases = []
  } finally {
    dialog.patternLoading = false
  }
}

const fetchApprovals = async () => {
  loading.value = true
  try {
    const params = {}
    if (activeTab.value === 'pending') params.status_filter = 'pending'
    else if (activeTab.value === 'mine') params.requester_id = currentUserId.value
    
    const data = await request.get('/approvals', { params })
    approvalList.value = data.items || data
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

const handleTabChange = () => fetchApprovals()

// 执行方式变更
const handleExecutionModeChange = (value) => {
  if (value !== 'scheduled') {
    dialog.form.scheduled_time = null
  }
}

// 禁用过去的日期
const disabledDate = (time) => {
  return time.getTime() < Date.now() - 24 * 60 * 60 * 1000
}

// 禁用过去的小时
const disabledHours = () => {
  if (!dialog.form.scheduled_time) return []
  const now = new Date()
  const selected = new Date(dialog.form.scheduled_time)
  if (selected.toDateString() === now.toDateString()) {
    return Array.from({ length: now.getHours() }, (_, i) => i)
  }
  return []
}

// 禁用过去的分钟
const disabledMinutes = (hour) => {
  if (!dialog.form.scheduled_time) return []
  const now = new Date()
  const selected = new Date(dialog.form.scheduled_time)
  if (selected.toDateString() === now.toDateString() && hour === now.getHours()) {
    return Array.from({ length: now.getMinutes() }, (_, i) => i)
  }
  return []
}

const handleAdd = () => {
  dialog.form = {
    title: '',
    instance_id: null,
    database_mode: 'single',
    database_name: '',
    database_list: [],
    database_pattern: '',
    change_type: 'DDL',
    sql_content: '',
    remark: '',
    execution_mode: 'auto', // 默认审批后自动执行
    scheduled_time: null
  }
  fullSqlContent.value = ''
  resetFileState()
  sqlValidation.show = false
  parsedDatabases.value = []
  dialog.databases = []
  dialog.matchedDatabases = []
  dialog.visible = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    const sqlToSubmit = fullSqlContent.value || dialog.form.sql_content
    if (!sqlToSubmit.trim()) {
      ElMessage.error('SQL内容不能为空')
      return
    }
    
    dialog.submitting = true
    try {
      const submitData = {
        title: dialog.form.title,
        change_type: dialog.form.change_type,
        instance_id: dialog.form.instance_id,
        sql_content: sqlToSubmit,
        sql_line_count: sqlStats.totalLines,
        database_mode: dialog.form.database_mode,
        remark: dialog.form.remark,
        affected_rows_estimate: dialog.form.affected_rows_estimate || 0,
        auto_execute: dialog.form.execution_mode === 'auto'
      }
      
      // 根据模式设置数据库相关字段
      switch (dialog.form.database_mode) {
        case 'single':
          submitData.database_name = dialog.form.database_name
          break
        case 'multiple':
          submitData.database_list = dialog.form.database_list
          break
        case 'pattern':
          submitData.database_pattern = dialog.form.database_pattern
          submitData.matched_database_count = dialog.matchedDatabases.length
          break
        case 'auto':
          submitData.parsed_databases = parsedDatabases.value
          break
      }
      
      // 添加定时执行时间
      if (dialog.form.execution_mode === 'scheduled' && dialog.form.scheduled_time) {
        submitData.scheduled_time = dayjs(dialog.form.scheduled_time).toISOString()
      }
      
      await request.post('/approvals', submitData)
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
    if (error !== 'cancel') console.error('审批失败:', error)
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

const formatTime = (time) => dayjs(time).format('YYYY-MM-DD HH:mm:ss')

onMounted(() => {
  // 处理 URL 参数中的 tab
  const tabParam = route.query.tab
  if (tabParam && ['pending', 'processed', 'mine'].includes(tabParam)) {
    activeTab.value = tabParam
  }
  
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
    &.low { background: #f0f9eb; color: #67c23a; }
    &.medium { background: #fdf6ec; color: #e6a23c; }
    &.high { background: #fef0f0; color: #f56c6c; }
    &.critical { background: #fde2e2; color: #f56c6c; font-weight: bold; }
  }
  
  .selected-count {
    margin-top: 5px;
    font-size: 12px;
    color: #909399;
  }
  
  .matched-databases {
    margin-top: 10px;
    padding: 10px;
    background: #f5f7fa;
    border-radius: 4px;
    
    .matched-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      font-size: 13px;
      color: #606266;
    }
    
    .matched-list {
      display: flex;
      flex-wrap: wrap;
    }
  }
  
  .db-count-info {
    margin-top: 10px;
    font-size: 13px;
    color: #606266;
  }
  
  .parsed-databases {
    margin-top: 10px;
    padding: 10px;
    background: #f0f9eb;
    border-radius: 4px;
    font-size: 13px;
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
        
        span { font-weight: 500; color: #606266; }
        .editor-actions { display: flex; gap: 5px; }
      }
      
      .sql-textarea {
        :deep(textarea) {
          border: none;
          border-radius: 0;
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 13px;
        }
      }
    }
    
    .validation-result {
      margin-top: 10px;
      
      .validation-title {
        display: flex;
        align-items: center;
        gap: 15px;
        .statement-count { font-size: 12px; color: #909399; }
      }
      
      .validation-errors {
        margin: 5px 0 0 0;
        padding-left: 20px;
        li { margin: 3px 0; }
      }
    }
  }
  
  .detail-sql-content {
    .sql-info { margin-bottom: 8px; }
    .sql-preview {
      background: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      font-family: monospace;
      font-size: 12px;
      max-height: 300px;
      overflow: auto;
      white-space: pre-wrap;
    }
  }
  
  .db-list-container {
    max-height: 400px;
    overflow: auto;
  }
  
  .scheduled-execution-wrapper {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    
    .scheduled-info {
      margin-top: 5px;
      width: 100%;
    }
  }
  
  .form-tip {
    margin-top: 8px;
    font-size: 12px;
    color: #909399;
    display: flex;
    align-items: center;
    gap: 4px;
  }
}
</style>
