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
            <el-input v-model="dbSearch" placeholder="搜索数据库" prefix-icon="Search" size="small" style="margin-bottom: 10px;" />
            <el-tree
              :data="databaseTree"
              :props="{ children: 'children', label: 'label' }"
              :filter-node-method="filterNode"
              ref="treeRef"
              @node-click="handleDbClick"
              highlight-current
            />
          </div>
        </el-card>
      </el-col>
      
      <!-- 右侧：SQL编辑器 -->
      <el-col :span="18">
        <el-card shadow="never" class="editor-card">
          <template #header>
            <div class="card-header">
              <span>SQL编辑器</span>
              <div>
                <el-button type="primary" @click="executeSQL" :loading="executing">
                  <el-icon><VideoPlay /></el-icon>
                  执行
                </el-button>
                <el-button @click="formatSQL">格式化</el-button>
                <el-button @click="clearSQL">清空</el-button>
              </div>
            </div>
          </template>
          
          <div class="editor-wrapper">
            <el-input
              v-model="sqlContent"
              type="textarea"
              :rows="12"
              placeholder="请输入SQL语句"
              class="sql-textarea"
            />
          </div>
          
          <!-- 执行结果 -->
          <div v-if="result" class="result-section">
            <el-divider content-position="left">执行结果</el-divider>
            <el-alert
              :title="result.message"
              :type="result.success ? 'success' : 'error'"
              :closable="false"
              show-icon
              style="margin-bottom: 10px;"
            />
            
            <div v-if="result.success && result.data?.length" class="result-table">
              <el-table :data="result.data" style="width: 100%" max-height="400">
                <el-table-column
                  v-for="col in result.columns"
                  :key="col"
                  :prop="col"
                  :label="col"
                  show-overflow-tooltip
                />
              </el-table>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { ElMessage } from 'element-plus'

const instances = ref([])
const selectedInstance = ref(null)
const selectedDatabase = ref(null)
const databases = ref([])
const tables = ref({})
const dbSearch = ref('')
const treeRef = ref(null)
const sqlContent = ref('')
const executing = ref(false)
const result = ref(null)

const databaseTree = ref([])

const fetchInstances = async () => {
  try {
    instances.value = await instancesApi.getList({ limit: 100 })
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleInstanceChange = async () => {
  selectedDatabase.value = null
  result.value = null
  try {
    const data = await request.get(`/sql/databases/${selectedInstance.value}`)
    databases.value = data
    
    // 构建树形结构
    databaseTree.value = data.map(db => ({
      label: db,
      value: db,
      children: []
    }))
    
    // 加载表
    for (const db of data.slice(0, 10)) { // 只加载前10个数据库的表
      try {
        const tablesData = await request.get(`/sql/tables/${selectedInstance.value}/${db}`)
        const dbNode = databaseTree.value.find(d => d.value === db)
        if (dbNode) {
          dbNode.children = tablesData.map(t => ({
            label: t,
            value: t,
            parent: db
          }))
        }
      } catch (error) {
        console.error(`获取数据库 ${db} 的表失败:`, error)
      }
    }
  } catch (error) {
    console.error('获取数据库列表失败:', error)
  }
}

const filterNode = (value, data) => {
  if (!value) return true
  return data.label.toLowerCase().includes(value.toLowerCase())
}

const handleDbClick = (data) => {
  if (data.parent) {
    selectedDatabase.value = data.parent
    sqlContent.value = `SELECT * FROM ${data.value} LIMIT 100;`
  } else {
    selectedDatabase.value = data.value
    sqlContent.value = `USE ${data.value};`
  }
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
  
  try {
    result.value = await request.post('/sql/execute', {
      instance_id: selectedInstance.value,
      database_name: selectedDatabase.value,
      sql: sqlContent.value,
      need_snapshot: true
    })
  } catch (error) {
    console.error('执行SQL失败:', error)
  } finally {
    executing.value = false
  }
}

const formatSQL = () => {
  // 简单的SQL格式化
  sqlContent.value = sqlContent.value
    .replace(/\s+/g, ' ')
    .replace(/\s*,\s*/g, ',\n  ')
    .replace(/\s+FROM\s+/gi, '\nFROM ')
    .replace(/\s+WHERE\s+/gi, '\nWHERE ')
    .replace(/\s+GROUP BY\s+/gi, '\nGROUP BY ')
    .replace(/\s+ORDER BY\s+/gi, '\nORDER BY ')
    .replace(/\s+LIMIT\s+/gi, '\nLIMIT ')
    .trim()
}

const clearSQL = () => {
  sqlContent.value = ''
  result.value = null
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
  }
  
  .editor-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .editor-wrapper {
      .sql-textarea {
        :deep(textarea) {
          font-family: 'Consolas', 'Monaco', monospace;
          font-size: 14px;
          line-height: 1.5;
        }
      }
    }
    
    .result-section {
      margin-top: 20px;
      
      .result-table {
        margin-top: 10px;
      }
    }
  }
}
</style>
