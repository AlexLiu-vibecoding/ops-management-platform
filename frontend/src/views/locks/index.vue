<template>
  <div class="locks-page">
    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" class="tabs-container">
      <!-- 锁等待监控 -->
      <el-tab-pane label="锁等待监控" name="locks">
        <el-card shadow="never" class="toolbar-card">
          <div class="toolbar">
            <el-select v-model="lockFilters.instance_id" placeholder="选择实例" clearable style="width: 200px">
              <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
            </el-select>
            <el-button type="primary" @click="checkLocks" :loading="checkingLocks" :disabled="!lockFilters.instance_id">
              检测锁等待
            </el-button>
            <el-input-number v-model="lockThreshold" :min="1" :max="3600" style="width: 120px" />
            <span class="threshold-label">秒以上</span>
          </div>
        </el-card>

        <el-card shadow="never" class="table-card">
          <el-table :data="locks" v-loading="loadingLocks" style="width: 100%">
            <el-table-column prop="instance_name" label="实例" min-width="120" />
            <el-table-column prop="database_name" label="数据库" width="100" />
            <el-table-column prop="wait_type" label="等待类型" width="100" align="center" />
            <el-table-column prop="waiting_thread_id" label="等待线程" width="100" align="center" />
            <el-table-column prop="waiting_sql" label="等待SQL" min-width="200">
              <template #default="{ row }">
                <span class="sql-text">{{ row.waiting_sql || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="waiting_time" label="等待时间(秒)" width="100" align="center">
              <template #default="{ row }">
                <el-tag :type="row.waiting_time > 60 ? 'danger' : 'warning'" size="small">
                  {{ row.waiting_time }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="blocking_thread_id" label="阻塞线程" width="100" align="center" />
            <el-table-column prop="status" label="状态" min-width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'danger' : 'success'" size="small">
                  {{ row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="发现时间" width="160">
              <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 长事务监控 -->
      <el-tab-pane label="长事务监控" name="transactions">
        <el-card shadow="never" class="toolbar-card">
          <div class="toolbar">
            <el-select v-model="trxFilters.instance_id" placeholder="选择实例" clearable style="width: 200px">
              <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
            </el-select>
            <el-button type="primary" @click="checkTransactions" :loading="checkingTrx" :disabled="!trxFilters.instance_id">
              检测长事务
            </el-button>
            <el-input-number v-model="trxThreshold" :min="1" :max="3600" style="width: 120px" />
            <span class="threshold-label">秒以上</span>
          </div>
        </el-card>

        <el-card shadow="never" class="table-card">
          <el-table :data="transactions" v-loading="loadingTrx" style="width: 100%">
            <el-table-column prop="instance_name" label="实例" min-width="120" />
            <el-table-column prop="database_name" label="数据库" width="100" />
            <el-table-column prop="trx_thread_id" label="线程ID" width="100" align="center" />
            <el-table-column prop="trx_started" label="开始时间" width="160">
              <template #default="{ row }">{{ formatTime(row.trx_started) }}</template>
            </el-table-column>
            <el-table-column prop="trx_duration" label="持续时间(秒)" width="120" align="center">
              <template #default="{ row }">
                <el-tag :type="row.trx_duration > 300 ? 'danger' : 'warning'" size="small">
                  {{ row.trx_duration }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="trx_state" label="状态" min-width="100" align="center" />
            <el-table-column prop="trx_query" label="当前SQL" min-width="200">
              <template #default="{ row }">
                <span class="sql-text">{{ row.trx_query || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="trx_rows_locked" label="锁定行数" width="100" align="center" />
            <el-table-column prop="user" label="用户" width="100" />
            <el-table-column prop="status" label="状态" min-width="70" align="center">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'danger' : 'info'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="60" fixed="right" align="center">
              <template #default="{ row }">
                <TableActions :row="row" :actions="transactionActions" @kill="killTransaction" />
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/index'
import TableActions from '@/components/TableActions.vue'

// 操作列配置
const lockActions = [
  { key: 'kill', label: 'Kill', event: 'kill', danger: true, primary: true }
]

const transactionActions = computed(() => [
  { 
    key: 'kill', 
    label: 'Kill', 
    event: 'kill', 
    danger: true, 
    primary: true,
    visible: (row) => row.status === 'active'
  }
])

const activeTab = ref('locks')
const instances = ref([])

// 锁等待
const locks = ref([])
const loadingLocks = ref(false)
const checkingLocks = ref(false)
const lockThreshold = ref(5)
const lockFilters = reactive({ instance_id: null })

// 长事务
const transactions = ref([])
const loadingTrx = ref(false)
const checkingTrx = ref(false)
const trxThreshold = ref(60)
const trxFilters = reactive({ instance_id: null })

const fetchInstances = async () => {
  try {
    const res = await request.get('/instances', { params: { limit: 100 } })
    instances.value = (res.items || []).filter(i => i.db_type === 'mysql')
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const fetchLocks = async () => {
  loadingLocks.value = true
  try {
    const res = await request.get('/monitor-ext/locks', { params: lockFilters })
    locks.value = res.items || []
  } catch (error) {
    console.error('获取锁等待失败:', error)
  } finally {
    loadingLocks.value = false
  }
}

const checkLocks = async () => {
  if (!lockFilters.instance_id) {
    ElMessage.warning('请选择实例')
    return
  }
  
  checkingLocks.value = true
  try {
    const res = await request.post(`/monitor-ext/locks/check/${lockFilters.instance_id}?threshold=${lockThreshold.value}`)
    ElMessage.success(res.message || '检测完成')
    fetchLocks()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '检测失败')
  } finally {
    checkingLocks.value = false
  }
}

const fetchTransactions = async () => {
  loadingTrx.value = true
  try {
    const res = await request.get('/monitor-ext/transactions', { params: trxFilters })
    transactions.value = res.items || []
  } catch (error) {
    console.error('获取长事务失败:', error)
  } finally {
    loadingTrx.value = false
  }
}

const checkTransactions = async () => {
  if (!trxFilters.instance_id) {
    ElMessage.warning('请选择实例')
    return
  }
  
  checkingTrx.value = true
  try {
    const res = await request.post(`/monitor-ext/transactions/check/${trxFilters.instance_id}?threshold=${trxThreshold.value}`)
    ElMessage.success(res.message || '检测完成')
    fetchTransactions()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '检测失败')
  } finally {
    checkingTrx.value = false
  }
}

const killTransaction = (row) => {
  ElMessageBox.confirm(`确定要Kill事务线程 ${row.trx_thread_id} 吗？`, '警告', { type: 'warning' }).then(async () => {
    try {
      await request.post(`/monitor-ext/transactions/kill/${row.trx_thread_id}?instance_id=${row.instance_id}`)
      ElMessage.success('事务已被Kill')
      fetchTransactions()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || 'Kill失败')
    }
  }).catch(() => {})
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  fetchInstances()
  fetchLocks()
  fetchTransactions()
})
</script>

<style lang="scss" scoped>
.locks-page {
  .tabs-container {
    :deep(.el-tabs__header) {
      margin-bottom: 0;
    }
  }
  
  .toolbar-card {
    margin-bottom: 20px;
    
    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
      
      .threshold-label {
        font-size: 14px;
        color: #606266;
      }
    }
  }
  
  .table-card {
    margin-bottom: 20px;
  }
  
  .sql-text {
    font-family: monospace;
    font-size: 12px;
    color: #606266;
  }
}
</style>
