<template>
  <div class="replication-page">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-select v-model="selectedInstance" placeholder="选择实例" style="width: 200px" clearable>
          <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
        </el-select>
        <el-button type="primary" @click="checkReplication" :loading="checking" :disabled="!selectedInstance">
          <el-icon><Refresh /></el-icon>
          检查状态
        </el-button>
        <el-button @click="fetchReplications">刷新列表</el-button>
      </div>
    </el-card>

    <!-- 复制状态列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="replications" v-loading="loading" style="width: 100%">
        <el-table-column prop="instance_name" label="主库实例" min-width="150" />
        <el-table-column prop="slave_host" label="从库地址" min-width="150">
          <template #default="{ row }">
            {{ row.slave_host }}:{{ row.slave_port }}
          </template>
        </el-table-column>
        <el-table-column prop="slave_io_running" label="IO线程" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.slave_io_running === 'Yes' ? 'success' : 'danger'" size="small">
              {{ row.slave_io_running || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="slave_sql_running" label="SQL线程" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.slave_sql_running === 'Yes' ? 'success' : 'danger'" size="small">
              {{ row.slave_sql_running || '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="seconds_behind_master" label="延迟(秒)" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getDelayType(row.seconds_behind_master)" size="small">
              {{ row.seconds_behind_master ?? '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="master_log_file" label="主库日志文件" min-width="150" />
        <el-table-column prop="check_time" label="检查时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.check_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="100" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.limit"
          :total="pagination.total"
          :page-sizes="[20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchReplications"
          @current-change="fetchReplications"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailDialog.visible" title="复制状态详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="主库实例">{{ detailDialog.data.instance_name }}</el-descriptions-item>
        <el-descriptions-item label="从库地址">{{ detailDialog.data.slave_host }}:{{ detailDialog.data.slave_port }}</el-descriptions-item>
        <el-descriptions-item label="IO线程状态">
          <el-tag :type="detailDialog.data.slave_io_running === 'Yes' ? 'success' : 'danger'" size="small">
            {{ detailDialog.data.slave_io_running }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="SQL线程状态">
          <el-tag :type="detailDialog.data.slave_sql_running === 'Yes' ? 'success' : 'danger'" size="small">
            {{ detailDialog.data.slave_sql_running }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="延迟秒数">
          <el-tag :type="getDelayType(detailDialog.data.seconds_behind_master)" size="small">
            {{ detailDialog.data.seconds_behind_master ?? '-' }} 秒
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="检查时间">{{ formatTime(detailDialog.data.check_time) }}</el-descriptions-item>
        <el-descriptions-item label="主库日志文件">{{ detailDialog.data.master_log_file }}</el-descriptions-item>
        <el-descriptions-item label="读取位置">{{ detailDialog.data.read_master_log_pos }}</el-descriptions-item>
        <el-descriptions-item label="中继日志文件">{{ detailDialog.data.relay_master_log_file }}</el-descriptions-item>
        <el-descriptions-item label="执行位置">{{ detailDialog.data.exec_master_log_pos }}</el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.last_io_error" label="IO错误" :span="2">
          <pre class="error-text">{{ detailDialog.data.last_io_error }}</pre>
        </el-descriptions-item>
        <el-descriptions-item v-if="detailDialog.data.last_sql_error" label="SQL错误" :span="2">
          <pre class="error-text">{{ detailDialog.data.last_sql_error }}</pre>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import request from '@/api/index'

const instances = ref([])
const replications = ref([])
const loading = ref(false)
const checking = ref(false)
const selectedInstance = ref(null)

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const detailDialog = reactive({
  visible: false,
  data: {}
})

const fetchInstances = async () => {
  try {
    const res = await request.get('/instances', { params: { limit: 100 } })
    instances.value = (res.items || []).filter(i => i.db_type === 'mysql')
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const fetchReplications = async () => {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      limit: pagination.limit
    }
    const res = await request.get('/monitor-ext/replication', { params })
    replications.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    console.error('获取复制状态失败:', error)
  } finally {
    loading.value = false
  }
}

const checkReplication = async () => {
  if (!selectedInstance.value) {
    ElMessage.warning('请选择实例')
    return
  }
  
  checking.value = true
  try {
    const res = await request.post(`/monitor-ext/replication/check/${selectedInstance.value}`)
    ElMessage.success(res.message || '检查完成')
    fetchReplications()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '检查失败')
  } finally {
    checking.value = false
  }
}

const viewDetail = (row) => {
  detailDialog.data = row
  detailDialog.visible = true
}

const getDelayType = (delay) => {
  if (delay === null || delay === undefined) return 'info'
  if (delay === 0) return 'success'
  if (delay <= 10) return 'warning'
  return 'danger'
}

const formatTime = (time) => {
  if (!time) return '-'
  return new Date(time).toLocaleString()
}

onMounted(() => {
  fetchInstances()
  fetchReplications()
})
</script>

<style lang="scss" scoped>
.replication-page {
  .toolbar-card {
    margin-bottom: 20px;
    
    .toolbar {
      display: flex;
      gap: 12px;
      align-items: center;
    }
  }
  
  .table-card {
    .pagination-container {
      display: flex;
      justify-content: flex-end;
      margin-top: 20px;
    }
  }
  
  .error-text {
    margin: 0;
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 12px;
    color: #F56C6C;
    background: #fef0f0;
    padding: 8px;
    border-radius: 4px;
  }
}
</style>
