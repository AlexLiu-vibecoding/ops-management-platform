<template>
  <div class="registrations-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>注册审批</span>
          <div class="header-actions">
            <el-select v-model="statusFilter" placeholder="筛选状态" style="width: 120px;" @change="fetchRegistrations">
              <el-option label="全部" value="" />
              <el-option label="待审批" value="pending" />
              <el-option label="已通过" value="approved" />
              <el-option label="已拒绝" value="rejected" />
            </el-select>
            <el-button @click="fetchRegistrations">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
          </div>
        </div>
      </template>
      
      <el-table :data="registrations" style="width: 100%" v-loading="loading">
        <el-table-column prop="username" label="用户名" min-width="80" show-overflow-tooltip />
        <el-table-column prop="real_name" label="姓名" min-width="70" show-overflow-tooltip />
        <el-table-column prop="email" label="邮箱" min-width="120" show-overflow-tooltip />
        <el-table-column prop="phone" label="手机号" width="110">
          <template #default="{ row }">
            {{ row.phone || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="申请理由" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reason || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="申请时间" width="160">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="reviewer_name" label="审批人" width="80" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.reviewer_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="140" fixed="right" align="center">
          <template #default="{ row }">
            <template v-if="row.status === 'pending'">
              <el-button type="success" size="small" @click="handleReview(row, true)">
                通过
              </el-button>
              <el-button type="danger" size="small" @click="handleReview(row, false)">
                拒绝
              </el-button>
            </template>
            <el-button v-else type="primary" text size="small" @click="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="注册申请详情" width="500px">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="用户名">{{ detailData?.username }}</el-descriptions-item>
        <el-descriptions-item label="真实姓名">{{ detailData?.real_name }}</el-descriptions-item>
        <el-descriptions-item label="邮箱">{{ detailData?.email }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ detailData?.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="申请理由">{{ detailData?.reason || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(detailData?.status)" size="small">
            {{ getStatusLabel(detailData?.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="申请时间">{{ formatTime(detailData?.created_at) }}</el-descriptions-item>
        <el-descriptions-item v-if="detailData?.reviewer_name" label="审批人">
          {{ detailData?.reviewer_name }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailData?.review_time" label="审批时间">
          {{ formatTime(detailData?.review_time) }}
        </el-descriptions-item>
        <el-descriptions-item v-if="detailData?.review_comment" label="审批意见">
          {{ detailData?.review_comment }}
        </el-descriptions-item>
      </el-descriptions>
      
      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import dayjs from 'dayjs'

const loading = ref(false)
const registrations = ref([])
const statusFilter = ref('pending')
const detailVisible = ref(false)
const detailData = ref(null)

const fetchRegistrations = async () => {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) {
      params.status_filter = statusFilter.value
    }
    registrations.value = await request.get('/auth/registrations', { params })
  } catch (error) {
    console.error('获取注册列表失败:', error)
    ElMessage.error('获取注册列表失败')
  } finally {
    loading.value = false
  }
}

const handleReview = async (row, approved) => {
  try {
    const action = approved ? '通过' : '拒绝'
    const { value } = await ElMessageBox.prompt(
      `确定要${action}该注册申请吗？`,
      `${action}申请`,
      {
        inputType: 'textarea',
        inputPlaceholder: '请输入审批意见（可选）',
        confirmButtonText: '确定',
        cancelButtonText: '取消'
      }
    )
    
    await request.post(`/auth/registrations/${row.id}/review`, {
      approved: approved,
      comment: value || ''
    })
    
    ElMessage.success(`已${action}该注册申请`)
    fetchRegistrations()
  } catch (error) {
    if (error !== 'cancel') {
      const errorMsg = error.response?.data?.detail || '操作失败'
      ElMessage.error(errorMsg)
    }
  }
}

const showDetail = (row) => {
  detailData.value = row
  detailVisible.value = true
}

const getStatusType = (status) => {
  const types = {
    pending: 'warning',
    approved: 'success',
    rejected: 'danger'
  }
  return types[status] || 'info'
}

const getStatusLabel = (status) => {
  const labels = {
    pending: '待审批',
    approved: '已通过',
    rejected: '已拒绝'
  }
  return labels[status] || status
}

const formatTime = (time) => {
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchRegistrations()
})
</script>

<style lang="scss" scoped>
.registrations-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }
}
</style>
