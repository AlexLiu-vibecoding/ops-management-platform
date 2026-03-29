<template>
  <div class="sql-optimizer">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">SQL优化器</h1>
          <p class="page-subtitle">智能分析SQL性能，提供优化建议</p>
        </div>
        <div class="header-right">
          <el-button @click="showSyncDialog = true" :icon="Refresh">
            同步表结构
          </el-button>
        </div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧：SQL输入 -->
      <div class="left-panel">
        <div class="panel-card">
          <div class="panel-header">
            <span class="panel-title">SQL输入</span>
            <div class="panel-actions">
              <el-select v-model="selectedInstance" placeholder="选择实例" style="width: 200px" @change="onInstanceChange">
                <el-option
                  v-for="instance in instances"
                  :key="instance.id"
                  :label="instance.name"
                  :value="instance.id"
                />
              </el-select>
              <el-select v-model="selectedDatabase" placeholder="选择数据库" style="width: 180px" :disabled="!selectedInstance">
                <el-option
                  v-for="db in databases"
                  :key="db"
                  :label="db"
                  :value="db"
                />
              </el-select>
            </div>
          </div>
          
          <div class="sql-editor">
            <el-input
              v-model="sqlText"
              type="textarea"
              :rows="12"
              placeholder="请输入需要分析的SQL语句..."
              resize="none"
            />
          </div>

          <div class="editor-footer">
            <div class="options">
              <el-checkbox v-model="enableLlm">启用LLM深度分析</el-checkbox>
            </div>
            <el-button type="primary" @click="analyzeSql" :loading="analyzing" :disabled="!canAnalyze">
              <el-icon><Analysis /></el-icon>
              开始分析
            </el-button>
          </div>
        </div>

        <!-- 分析历史 -->
        <div class="panel-card history-panel">
          <div class="panel-header">
            <span class="panel-title">分析历史</span>
            <el-button text size="small" @click="loadHistory" :loading="loadingHistory">
              刷新
            </el-button>
          </div>
          
          <div class="history-list" v-loading="loadingHistory">
            <div
              v-for="item in history"
              :key="item.id"
              class="history-item"
              @click="loadHistoryDetail(item)"
            >
              <div class="history-sql">{{ item.sql_text }}</div>
              <div class="history-meta">
                <el-tag :type="getRiskTagType(item.risk_level)" size="small">
                  {{ getRiskLabel(item.risk_level) }}
                </el-tag>
                <span class="history-time">{{ formatTime(item.created_at) }}</span>
              </div>
            </div>
            <el-empty v-if="history.length === 0" description="暂无分析记录" :image-size="60" />
          </div>
        </div>
      </div>

      <!-- 右侧：分析结果 -->
      <div class="right-panel">
        <div v-if="!analysisResult" class="empty-result">
          <el-empty description="请输入SQL并点击分析">
            <template #image>
              <el-icon :size="64" color="#c0c4cc"><Document /></el-icon>
            </template>
          </el-empty>
        </div>

        <div v-else class="result-container">
          <!-- 摘要卡片 -->
          <div class="summary-cards">
            <div class="summary-card">
              <div class="summary-value">{{ analysisResult.summary.tables_involved?.length || 0 }}</div>
              <div class="summary-label">涉及表</div>
            </div>
            <div class="summary-card">
              <div class="summary-value" :class="getRiskClass(analysisResult.risk_level)">
                {{ getRiskLabel(analysisResult.risk_level) }}
              </div>
              <div class="summary-label">风险等级</div>
            </div>
            <div class="summary-card">
              <div class="summary-value">{{ analysisResult.summary.issues_count || 0 }}</div>
              <div class="summary-label">发现问题</div>
            </div>
            <div class="summary-card">
              <div class="summary-value">{{ formatNumber(analysisResult.summary.total_rows_scanned) }}</div>
              <div class="summary-label">预计扫描行</div>
            </div>
          </div>

          <!-- 问题列表 -->
          <div class="result-section" v-if="analysisResult.rule_issues?.length">
            <div class="section-header">
              <span class="section-title">规则检测结果</span>
              <el-tag type="warning" size="small">{{ analysisResult.rule_issues.length }} 个问题</el-tag>
            </div>
            <div class="issues-list">
              <div
                v-for="(issue, index) in analysisResult.rule_issues"
                :key="index"
                class="issue-item"
                :class="`issue-${issue.severity}`"
              >
                <div class="issue-header">
                  <el-tag :type="getSeverityTagType(issue.severity)" size="small">
                    {{ getSeverityLabel(issue.severity) }}
                  </el-tag>
                  <span class="issue-title">{{ issue.title }}</span>
                </div>
                <div class="issue-description">{{ issue.description }}</div>
                <div class="issue-suggestion">
                  <el-icon><InfoFilled /></el-icon>
                  {{ issue.suggestion }}
                </div>
              </div>
            </div>
          </div>

          <!-- EXPLAIN结果 -->
          <div class="result-section">
            <div class="section-header">
              <span class="section-title">执行计划</span>
            </div>
            <el-table
              :data="analysisResult.explain_result"
              border
              size="small"
              max-height="300"
            >
              <el-table-column prop="id" label="ID" width="60" />
              <el-table-column prop="select_type" label="类型" width="100" />
              <el-table-column prop="table" label="表" width="120" />
              <el-table-column prop="type" label="访问类型" width="90">
                <template #default="{ row }">
                  <el-tag :type="getExplainTypeTag(row.type)" size="small">
                    {{ row.type || '-' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="possible_keys" label="可能索引" min-width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.possible_keys || '-' }}</template>
              </el-table-column>
              <el-table-column prop="key" label="使用索引" width="120" show-overflow-tooltip>
                <template #default="{ row }">{{ row.key || '-' }}</template>
              </el-table-column>
              <el-table-column prop="rows" label="扫描行" width="90">
                <template #default="{ row }">
                  <span :class="{ 'text-danger': row.rows > 10000 }">
                    {{ formatNumber(row.rows) }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column prop="Extra" label="Extra" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">{{ row.Extra || '-' }}</template>
              </el-table-column>
            </el-table>
          </div>

          <!-- LLM建议 -->
          <div class="result-section" v-if="analysisResult.llm_suggestions">
            <div class="section-header">
              <span class="section-title">AI优化建议</span>
              <el-tag type="success" size="small">
                <el-icon><Cpu /></el-icon>
                LLM分析
              </el-tag>
            </div>
            <div class="llm-content" v-html="formatMarkdown(analysisResult.llm_suggestions)"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 同步表结构对话框 -->
    <el-dialog
      v-model="showSyncDialog"
      title="同步表结构"
      width="500px"
    >
      <el-form :model="syncForm" label-width="100px">
        <el-form-item label="选择实例">
          <el-select v-model="syncForm.instance_id" placeholder="请选择实例" style="width: 100%">
            <el-option
              v-for="instance in instances"
              :key="instance.id"
              :label="instance.name"
              :value="instance.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="数据库">
          <el-input v-model="syncForm.database_name" placeholder="留空则同步所有库" />
        </el-form-item>
        <el-form-item label="表名">
          <el-input v-model="syncForm.table_names_str" placeholder="留空则同步所有表，多个表用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSyncDialog = false">取消</el-button>
        <el-button type="primary" @click="syncSchema" :loading="syncing">开始同步</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Refresh, Document, InfoFilled, Cpu, Operation
} from '@element-plus/icons-vue'
import { sqlOptimizerApi } from '@/api/sql-optimizer'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import dayjs from 'dayjs'

// 数据
const instances = ref([])
const databases = ref([])
const selectedInstance = ref(null)
const selectedDatabase = ref('')
const sqlText = ref('')
const enableLlm = ref(true)
const analyzing = ref(false)
const analysisResult = ref(null)

// 历史记录
const history = ref([])
const loadingHistory = ref(false)

// 同步对话框
const showSyncDialog = ref(false)
const syncing = ref(false)
const syncForm = reactive({
  instance_id: null,
  database_name: '',
  table_names_str: ''
})

// 计算属性
const canAnalyze = computed(() => {
  return selectedInstance.value && selectedDatabase.value && sqlText.value.trim()
})

// 加载实例列表
const loadInstances = async () => {
  try {
    const data = await instancesApi.getList()
    // 过滤掉 Redis 实例，SQL 优化器不支持 Redis
    instances.value = (data.items || data || []).filter(inst => inst.db_type !== 'redis')
  } catch (error) {
    console.error('加载实例列表失败:', error)
  }
}

// 实例变更
const onInstanceChange = async () => {
  databases.value = []
  selectedDatabase.value = ''
  
  if (!selectedInstance.value) return
  
  try {
    // 获取实例的真实数据库列表
    const data = await request.get(`/sql/databases/${selectedInstance.value}`)
    // 过滤系统数据库
    const systemDbs = ['information_schema', 'mysql', 'performance_schema', 'sys', 'template0', 'template1']
    databases.value = (data || []).filter(db => !systemDbs.includes(db))
  } catch (error) {
    console.error('获取数据库列表失败:', error)
    ElMessage.error('获取数据库列表失败')
  }
}

// 分析SQL
const analyzeSql = async () => {
  if (!canAnalyze.value) {
    ElMessage.warning('请选择实例和数据库，并输入SQL语句')
    return
  }
  
  analyzing.value = true
  analysisResult.value = null
  
  try {
    const result = await sqlOptimizerApi.analyze({
      instance_id: selectedInstance.value,
      database_name: selectedDatabase.value,
      sql_text: sqlText.value,
      enable_llm: enableLlm.value
    })
    
    analysisResult.value = result
    
    // 处理自动同步提示
    if (result.auto_sync_info) {
      const { synced, refreshed, failed } = result.auto_sync_info
      if (synced && synced.length > 0) {
        ElMessage.success(`已自动同步表结构: ${synced.join(', ')}`)
      }
      if (refreshed && refreshed.length > 0) {
        ElMessage.info(`已刷新过期表结构: ${refreshed.join(', ')}`)
      }
      if (failed && failed.length > 0) {
        const failedMsg = failed.map(f => `${f.table}: ${f.error}`).join('; ')
        ElMessage.warning(`部分表同步失败: ${failedMsg}`)
      }
    }
    
    // 刷新历史
    loadHistory()
    
    ElMessage.success('分析完成')
  } catch (error) {
    ElMessage.error('分析失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    analyzing.value = false
  }
}

// 加载历史
const loadHistory = async () => {
  if (!selectedInstance.value) return
  
  loadingHistory.value = true
  try {
    const data = await sqlOptimizerApi.getHistory(selectedInstance.value)
    history.value = data || []
  } catch (error) {
    console.error('加载历史失败:', error)
  } finally {
    loadingHistory.value = false
  }
}

// 加载历史详情
const loadHistoryDetail = async (item) => {
  try {
    const detail = await sqlOptimizerApi.getHistoryDetail(item.id)
    analysisResult.value = detail
    sqlText.value = detail.sql_text
    
    // 如果历史记录的实例与当前选择不一致，更新选择
    if (detail.instance_id && detail.instance_id !== selectedInstance.value) {
      selectedInstance.value = detail.instance_id
      // 加载该实例的数据库列表
      onInstanceChange()
    }
    // 设置数据库选择
    if (detail.database_name) {
      selectedDatabase.value = detail.database_name
    }
  } catch (error) {
    ElMessage.error('加载详情失败')
  }
}

// 同步表结构
const syncSchema = async () => {
  if (!syncForm.instance_id) {
    ElMessage.warning('请选择实例')
    return
  }
  
  syncing.value = true
  try {
    const tableNames = syncForm.table_names_str
      ? syncForm.table_names_str.split(',').map(t => t.trim()).filter(Boolean)
      : null
    
    await sqlOptimizerApi.syncSchema({
      instance_id: syncForm.instance_id,
      database_name: syncForm.database_name || null,
      table_names: tableNames
    })
    
    ElMessage.success('表结构同步成功')
    showSyncDialog.value = false
  } catch (error) {
    ElMessage.error('同步失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    syncing.value = false
  }
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('MM-DD HH:mm')
}

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  if (num >= 10000) {
    return (num / 10000).toFixed(1) + 'w'
  }
  return num.toLocaleString()
}

// 风险等级
const getRiskLabel = (level) => {
  const map = {
    low: '低',
    medium: '中',
    high: '高',
    critical: '严重'
  }
  return map[level] || level
}

const getRiskTagType = (level) => {
  const map = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger'
  }
  return map[level] || 'info'
}

const getRiskClass = (level) => {
  return `risk-${level}`
}

// 严重程度
const getSeverityLabel = (severity) => {
  const map = {
    info: '信息',
    warning: '警告',
    error: '错误',
    critical: '严重'
  }
  return map[severity] || severity
}

const getSeverityTagType = (severity) => {
  const map = {
    info: 'info',
    warning: 'warning',
    error: 'danger',
    critical: 'danger'
  }
  return map[severity] || 'info'
}

// EXPLAIN类型标签
const getExplainTypeTag = (type) => {
  const goodTypes = ['const', 'eq_ref', 'ref', 'range']
  const badTypes = ['ALL', 'index']
  
  if (goodTypes.includes(type)) return 'success'
  if (badTypes.includes(type)) return 'danger'
  return 'warning'
}

// 格式化Markdown
const formatMarkdown = (text) => {
  if (!text) return ''
  // 简单的Markdown转HTML
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/```sql\n([\s\S]+?)```/g, '<pre class="code-block"><code>$1</code></pre>')
    .replace(/```(\w*)\n([\s\S]+?)```/g, '<pre class="code-block"><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    .replace(/\n/g, '<br>')
}

// 初始化
onMounted(() => {
  loadInstances()
})
</script>

<style lang="scss" scoped>
.sql-optimizer {
  padding: 20px;
  min-height: calc(100vh - 104px);
}

.page-header {
  margin-bottom: 20px;
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  
  .page-title {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 4px 0;
  }
  
  .page-subtitle {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0;
  }
}

.main-content {
  display: grid;
  grid-template-columns: 480px 1fr;
  gap: 20px;
  height: calc(100vh - 180px);
}

.left-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.right-panel {
  overflow: auto;
}

.panel-card {
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--separator);
  backdrop-filter: blur(10px);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--separator);
  
  .panel-title {
    font-size: 15px;
    font-weight: 600;
    color: var(--text-primary);
  }
  
  .panel-actions {
    display: flex;
    gap: 8px;
  }
}

.sql-editor {
  padding: 16px;
  
  :deep(.el-textarea__inner) {
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 13px;
    line-height: 1.6;
    background: var(--bg-secondary);
    border: 1px solid var(--separator);
    border-radius: 8px;
    padding: 12px;
    
    &:focus {
      border-color: var(--primary);
    }
  }
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid var(--separator);
  
  .options {
    display: flex;
    align-items: center;
    gap: 16px;
  }
}

.history-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  .panel-header {
    flex-shrink: 0;
  }
  
  .history-list {
    flex: 1;
    overflow-y: auto;
    padding: 8px;
  }
}

.history-item {
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 8px;
  border: 1px solid transparent;
  
  &:hover {
    background: var(--bg-secondary);
    border-color: var(--separator);
  }
  
  .history-sql {
    font-family: monospace;
    font-size: 12px;
    color: var(--text-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: 8px;
  }
  
  .history-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .history-time {
      font-size: 12px;
      color: var(--text-secondary);
    }
  }
}

.empty-result {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--separator);
}

.result-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.summary-card {
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--separator);
  padding: 16px;
  text-align: center;
  
  .summary-value {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    
    &.risk-low { color: var(--success); }
    &.risk-medium { color: var(--warning); }
    &.risk-high { color: var(--danger); }
    &.risk-critical { color: var(--danger); }
  }
  
  .summary-label {
    font-size: 13px;
    color: var(--text-secondary);
    margin-top: 4px;
  }
}

.result-section {
  background: var(--glass-bg);
  border-radius: 12px;
  border: 1px solid var(--separator);
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    border-bottom: 1px solid var(--separator);
    
    .section-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }
  }
}

.issues-list {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.issue-item {
  padding: 12px;
  border-radius: 8px;
  border-left: 3px solid var(--separator);
  background: var(--bg-secondary);
  
  &.issue-info { border-left-color: var(--info); }
  &.issue-warning { border-left-color: var(--warning); }
  &.issue-error { border-left-color: var(--danger); }
  &.issue-critical { border-left-color: var(--danger); background: rgba(var(--danger-rgb), 0.1); }
  
  .issue-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    
    .issue-title {
      font-weight: 600;
      color: var(--text-primary);
    }
  }
  
  .issue-description {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }
  
  .issue-suggestion {
    display: flex;
    align-items: flex-start;
    gap: 6px;
    font-size: 13px;
    color: var(--primary);
    background: var(--bg-tertiary);
    padding: 8px;
    border-radius: 6px;
    
    .el-icon {
      flex-shrink: 0;
      margin-top: 2px;
    }
  }
}

.llm-content {
  padding: 16px;
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-primary);
  
  :deep(.code-block) {
    background: var(--bg-secondary);
    padding: 12px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 12px 0;
    
    code {
      font-family: 'Monaco', 'Menlo', monospace;
      font-size: 13px;
    }
  }
  
  :deep(.inline-code) {
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
  }
  
  :deep(strong) {
    color: var(--primary);
  }
}

.text-danger {
  color: var(--danger);
  font-weight: 600;
}
</style>
