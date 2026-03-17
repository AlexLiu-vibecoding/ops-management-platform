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
    <el-dialog v-model="dialog.visible" title="提交变更申请" width="600px">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="dialog.form.title" placeholder="请输入变更标题" />
        </el-form-item>
        <el-form-item label="实例" prop="instance_id">
          <el-select v-model="dialog.form.instance_id" placeholder="请选择实例" style="width: 100%;" @change="handleInstanceSelect">
            <el-option v-for="inst in instances" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="数据库">
          <el-select v-model="dialog.form.database_name" placeholder="请选择数据库" style="width: 100%;">
            <el-option v-for="db in dialog.databases" :key="db" :label="db" :value="db" />
          </el-select>
        </el-form-item>
        <el-form-item label="变更类型" prop="change_type">
          <el-select v-model="dialog.form.change_type" placeholder="请选择变更类型" style="width: 100%;">
            <el-option label="DDL变更" value="DDL" />
            <el-option label="DML变更" value="DML" />
            <el-option label="运维操作" value="OPERATION" />
            <el-option label="自定义SQL" value="CUSTOM" />
          </el-select>
        </el-form-item>
        <el-form-item label="SQL内容" prop="sql_content">
          <el-input v-model="dialog.form.sql_content" type="textarea" :rows="8" placeholder="请输入SQL语句" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">提交</el-button>
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
import dayjs from 'dayjs'

const userStore = useUserStore()
const currentUserId = computed(() => userStore.user?.id)
const canApprove = computed(() => ['super_admin', 'approval_admin'].includes(userStore.user?.role))

const loading = ref(false)
const activeTab = ref('pending')
const approvalList = ref([])
const instances = ref([])
const formRef = ref(null)

const dialog = reactive({
  visible: false,
  databases: [],
  form: {
    title: '',
    instance_id: null,
    database_name: '',
    change_type: 'DDL',
    sql_content: ''
  },
  rules: {
    title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
    instance_id: [{ required: true, message: '请选择实例', trigger: 'change' }],
    change_type: [{ required: true, message: '请选择变更类型', trigger: 'change' }],
    sql_content: [{ required: true, message: '请输入SQL内容', trigger: 'blur' }]
  }
})

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
    instances.value = await instancesApi.getList({ limit: 100 })
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

const handleTabChange = () => {
  fetchApprovals()
}

const handleAdd = () => {
  dialog.visible = true
}

const handleInstanceSelect = async (instanceId) => {
  try {
    dialog.databases = await request.get(`/sql/databases/${instanceId}`)
  } catch (error) {
    console.error('获取数据库列表失败:', error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      await request.post('/approvals', dialog.form)
      ElMessage.success('提交成功')
      dialog.visible = false
      fetchApprovals()
    } catch (error) {
      console.error('提交失败:', error)
    }
  })
}

const handleView = (row) => {
  ElMessage.info('详情功能开发中')
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
    await ElMessageBox.confirm('确定要执行此变更吗？', '警告', { type: 'warning' })
    await request.post(`/approvals/${row.id}/execute`)
    ElMessage.success('执行成功')
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
}
</style>
