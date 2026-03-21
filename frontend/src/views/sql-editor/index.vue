<template>
  <div class="sql-editor-page">
    <el-row :gutter="20">
      <!-- 左侧：实例和数据库选择 -->
      <el-col :span="6">
        <el-card shadow="never" class="instance-card">
          <template #header>
            <span>选择实例</span>
          </template>
          <el-select v-model="selectedInstance" placeholder="请选择实例" style="width: 100%;" @change="handleInstanceChange">
            <el-option
              v-for="inst in instances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
          
          <div v-if="selectedInstance" class="database-list">
            <el-divider content-position="left">数据库</el-divider>
            <el-input v-model="dbSearch" placeholder="搜索数据库" prefix-icon="Search" size="small" style="margin-bottom: 10px;" @input="handleDbSearch" />
            <el-tree
              :data="databaseTree"
              :props="{ children: 'children', label: 'label' }"
              ref="treeRef"
              @node-click="handleDbClick"
              highlight-current
              :default-expand-all="false"
              node-key="value"
            >
              <template #default="{ node, data }">
                <span class="tree-node">
                  <el-icon v-if="!data.children || data.children.length === 0" style="margin-right: 4px;"><Document /></el-icon>
                  <el-icon v-else style="margin-right: 4px;"><Folder /></el-icon>
                  <span>{{ node.label }}</span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：SQL编辑器 -->
      <el-col :span="18">
        <el-card shadow="never" class="editor-card">
          <template #header>
            <div class="card-header">
              <span>SQL编辑器</span>
              <div class="header-actions">
                <el-upload
                  ref="uploadRef"
                  :auto-upload="false"
                  :show-file-list="false"
                  accept=".sql,.txt"
                  :on-change="handleFileChange"
                >
                  <el-button type="info" plain>
                    <el-icon><Upload /></el-icon>
                    上传SQL文件
                  </el-button>
                </el-upload>
                <el-button type="primary" @click="executeSQL" :loading="executing">
                  <el-icon><VideoPlay /></el-icon>
                  执行
                </el-button>
                <el-button @click="formatSQL">格式化</el-button>
                <el-button @click="clearSQL">清空</el-button>
              </div>
            </div>
          </template>
          
          <!-- 当前选中的数据库 -->
          <div v-if="selectedDatabase" class="current-db">
            <el-tag type="success" effect="plain">
              当前数据库: {{ selectedDatabase }}
            </el-tag>
          </div>
          
          <div class="editor-wrapper">
            <el-input
              v-model="sqlContent"
              type="textarea"
              :rows="12"
              placeholder="请输入SQL语句，或上传SQL文件"
              class="sql-textarea"
            />
          </div>
          
          <!-- SQL语句列表（多语句执行时显示） -->
          <div v-if="sqlStatements.length > 1" class="statements-section">
            <el-divider content-position="left">SQL语句列表 (共{{ sqlStatements.length }}条)</el-divider>
            <div class="statements-list">
              <el-tag
                v-for="(stmt, idx) in sqlStatements"
                :key="idx"
                :type="stmtStatus[idx] || 'info'"
                class="statement-tag"
              >
                {{ idx + 1 }}. {{ stmt.substring(0, 30) }}{{ stmt.length > 30 ? '...' : '' }}
              </el-tag>
            </div>
          </div>
          
          <!-- 执行结果 -->
          <div v-if="result" class="result-section">
            <el-divider content-position="left">执行结果</el-divider>
            
            <!-- 执行统计 -->
            <div class="result-stats">
              <el-row :gutter="20">
                <el-col :span="6">
                  <div class="stat-item">
                    <span class="stat-label">执行状态</span>
                    <el-tag :type="result.success ? 'success' : 'danger'" size="large">
                      {{ result.success ? '成功' : '失败' }}
                    </el-tag>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item">
                    <span class="stat-label">影响行数</span>
                    <span class="stat-value">{{ result.affected_rows || 0 }}</span>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item">
                    <span class="stat-label">执行耗时</span>
                    <span class="stat-value">{{ (result.execution_time || 0).toFixed(3) }}s</span>
                  </div>
                </el-col>
                <el-col :span="6">
                  <div class="stat-item" v-if="result.snapshot_id">
                    <span class="stat-label">快照ID</span>
                    <el-tag type="warning">{{ result.snapshot_id }}</el-tag>
                  </div>
                </el-col>
              </el-row>
            </div>
            
            <el-alert
              :title="result.message"
              :type="result.success ? 'success' : 'error'"
              :closable="false"
              show-icon
              style="margin: 15px 0;"
            />
            
            <!-- 查询结果表格 -->
            <div v-if="result.success && result.data?.length" class="result-table">
              <div class="table-header">
                <span>查询结果 ({{ result.data.length }} 条记录)</span>
                <el-button size="small" @click="exportResult">
                  <el-icon><Download /></el-icon>
                  导出
                </el-button>
              </div>
              <el-table 
                :data="result.data" 
                style="width: 100%" 
                max-height="400"
                border
                stripe
              >
                <el-table-column
                  v-for="col in result.columns"
                  :key="col"
                  :prop="col"
                  :label="col"
                  show-overflow-tooltip
                  min-width="120"
                />
              </el-table>
            </div>
          </div>
          
          <!-- 执行历史 -->
          <div v-if="history.length > 0" class="history-section">
            <el-divider content-position="left">
              <span @click="showHistory = !showHistory" style="cursor: pointer;">
                执行历史 ({{ history.length }})
                <el-icon v-if="showHistory"><ArrowUp /></el-icon>
                <el-icon v-else><ArrowDown /></el-icon>
              </span>
            </el-divider>
            <el-collapse v-if="showHistory" accordion>
              <el-collapse-item
                v-for="(item, idx) in history.slice(0, 10)"
                :key="idx"
                :name="idx"
              >
                <template #title>
                  <div class="history-title">
                    <el-tag :type="item.success ? 'success' : 'danger'" size="small">
                      {{ item.success ? '成功' : '失败' }}
                    </el-tag>
                    <span class="history-time">{{ item.time }}</span>
                    <span class="history-sql">{{ item.sql.substring(0, 50) }}...</span>
                  </div>
                </template>
                <div class="history-detail">
                  <div><strong>实例:</strong> {{ item.instanceName }}</div>
                  <div><strong>数据库:</strong> {{ item.database || '未选择' }}</div>
                  <div><strong>SQL:</strong> <code>{{ item.sql }}</code></div>
                  <div><strong>结果:</strong> {{ item.message }}</div>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { ElMessage } from 'element-plus'
import { Document, Folder, Upload, VideoPlay, Download, ArrowUp, ArrowDown } from '@element-plus/icons-vue'

const instances = ref([])
const selectedInstance = ref(null)
const selectedDatabase = ref(null)
const databases = ref([])
const dbSearch = ref('')
const treeRef = ref(null)
const sqlContent = ref('')
const executing = ref(false)
const result = ref(null)
const uploadRef = ref(null)
const showHistory = ref(false)
const stmtStatus = ref({})

const history = ref([])

const databaseTree = ref([])

// 解析SQL语句
const sqlStatements = computed(() => {
  if (!sqlContent.value.trim()) return []
  // 按分号分割，过滤空语句
  return sqlContent.value
    .split(';')
    .map(s => s.trim())
    .filter(s => s.length > 0)
})

const fetchInstances = async () => {
  try {
    const data = await instancesApi.getList({ limit: 100 })
    instances.value = data.items || data
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleInstanceChange = async () => {
  selectedDatabase.value = null
  result.value = null
  databaseTree.value = []
  
  try {
    const data = await request.get(`/sql/databases/${selectedInstance.value}`)
    databases.value = data
    
    // 过滤系统数据库
    const systemDbs = ['information_schema', 'mysql', 'performance_schema', 'sys', 'template0', 'template1', '_supabase']
    const userDbs = data.filter(db => !systemDbs.includes(db))
    
    // 构建树形结构
    databaseTree.value = userDbs.map(db => ({
      label: db,
      value: db,
      children: []
    }))
  } catch (error) {
    console.error('获取数据库列表失败:', error)
    ElMessage.error('获取数据库列表失败')
  }
}

const handleDbSearch = () => {
  if (treeRef.value) {
    treeRef.value.filter(dbSearch.value)
  }
}

const filterNode = (value, data) => {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

const handleDbClick = async (data) => {
  if (data.children) {
    // 点击的是数据库节点
    selectedDatabase.value = data.value
    sqlContent.value = `USE ${data.value};`
    
    // 加载该数据库的表
    if (!data.children.length || data.children.length === 0) {
      try {
        const tablesData = await request.get(`/sql/tables/${selectedInstance.value}/${data.value}`)
        data.children = tablesData.map(t => ({
          label: t,
          value: t,
          parent: data.value
        }))
      } catch (error) {
        console.error('获取表列表失败:', error)
      }
    }
  } else {
    // 点击的是表节点
    selectedDatabase.value = data.parent
    sqlContent.value = `SELECT * FROM ${data.value} LIMIT 100;`
  }
}

const handleFileChange = (file) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    const content = e.target.result
    sqlContent.value = content
    ElMessage.success(`已加载文件: ${file.name}`)
  }
  reader.onerror = () => {
    ElMessage.error('文件读取失败')
  }
  reader.readAsText(file.raw)
}

const executeSQL = async () => {
  if (!selectedInstance.value) {
    ElMessage.warning('请先选择实例')
    return
  }
  
  if (!sqlContent.value.trim()) {
    ElMessage.warning('请输入SQL语句')
    return
  }
  
  executing.value = true
  result.value = null
  stmtStatus.value = {}
  
  const startTime = Date.now()
  
  try {
    const res = await request.post('/sql/execute', {
      instance_id: selectedInstance.value,
      database_name: selectedDatabase.value,
      sql: sqlContent.value,
      need_snapshot: true
    })
    
    result.value = res
    
    // 添加到历史
    const instanceName = instances.value.find(i => i.id === selectedInstance.value)?.name || ''
    history.value.unshift({
      sql: sqlContent.value,
      success: res.success,
      message: res.message,
      instanceName,
      database: selectedDatabase.value,
      time: new Date().toLocaleString(),
      executionTime: res.execution_time
    })
    
    // 保持历史记录不超过50条
    if (history.value.length > 50) {
      history.value = history.value.slice(0, 50)
    }
    
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(res.message)
    }
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || '执行失败'
    result.value = {
      success: false,
      message: errorMsg,
      execution_time: (Date.now() - startTime) / 1000
    }
    
    // 添加到历史
    const instanceName = instances.value.find(i => i.id === selectedInstance.value)?.name || ''
    history.value.unshift({
      sql: sqlContent.value,
      success: false,
      message: errorMsg,
      instanceName,
      database: selectedDatabase.value,
      time: new Date().toLocaleString()
    })
    
    ElMessage.error(errorMsg)
  } finally {
    executing.value = false
  }
}

const formatSQL = () => {
  if (!sqlContent.value.trim()) return
  
  // 简单的SQL格式化
  let formatted = sqlContent.value
    .replace(/\s+/g, ' ')
    .trim()
  
  // 关键字换行
  const keywords = ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN', 'ON', 'AND', 'OR', 'INSERT INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE FROM', 'CREATE TABLE', 'ALTER TABLE', 'DROP TABLE']
  
  keywords.forEach(keyword => {
    const regex = new RegExp(`\\b${keyword}\\b`, 'gi')
    formatted = formatted.replace(regex, '\n' + keyword)
  })
  
  sqlContent.value = formatted.trim()
  ElMessage.success('SQL已格式化')
}

const clearSQL = () => {
  sqlContent.value = ''
  result.value = null
  stmtStatus.value = {}
}

const exportResult = () => {
  if (!result.value?.data?.length) return
  
  const headers = result.value.columns
  const rows = result.value.data
  
  // 转换为CSV
  let csv = headers.join(',') + '\n'
  rows.forEach(row => {
    const values = headers.map(h => {
      const val = row[h]
      if (val === null || val === undefined) return ''
      if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
        return `"${val.replace(/"/g, '""')}"`
      }
      return val
    })
    csv += values.join(',') + '\n'
  })
  
  // 下载文件
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `query_result_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(link.href)
  
  ElMessage.success('导出成功')
}

onMounted(() => {
  fetchInstances()
})
</script>

<style lang="scss" scoped>
.sql-editor-page {
  .instance-card {
    height: calc(100vh - 160px);
    overflow: auto;
    
    .database-list {
      margin-top: 20px;
    }
    
    .tree-node {
      display: flex;
      align-items: center;
      font-size: 13px;
    }
  }
  
  .editor-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .header-actions {
        display: flex;
        gap: 10px;
      }
    }
    
    .current-db {
      margin-bottom: 10px;
    }
    
    .editor-wrapper {
      .sql-textarea {
        :deep(textarea) {
          font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
          font-size: 14px;
          line-height: 1.5;
          background-color: #1e1e1e;
          color: #d4d4d4;
        }
      }
    }
    
    .statements-section {
      margin-top: 15px;
      
      .statements-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        
        .statement-tag {
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }
    
    .result-section {
      margin-top: 20px;
      
      .result-stats {
        background: #f5f7fa;
        padding: 15px;
        border-radius: 4px;
        margin-bottom: 15px;
        
        .stat-item {
          text-align: center;
          
          .stat-label {
            display: block;
            font-size: 12px;
            color: #909399;
            margin-bottom: 5px;
          }
          
          .stat-value {
            font-size: 20px;
            font-weight: 600;
            color: #303133;
          }
        }
      }
      
      .result-table {
        .table-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 10px;
          font-weight: 500;
        }
      }
    }
    
    .history-section {
      margin-top: 20px;
      
      .history-title {
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
        
        .history-time {
          color: #909399;
          font-size: 12px;
        }
        
        .history-sql {
          color: #606266;
          font-family: monospace;
        }
      }
      
      .history-detail {
        font-size: 13px;
        line-height: 1.8;
        
        code {
          background: #f5f7fa;
          padding: 2px 6px;
          border-radius: 3px;
          font-family: monospace;
        }
      }
    }
  }
}
</style>
