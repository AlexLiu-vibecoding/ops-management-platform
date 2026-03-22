<template>
  <el-card shadow="never" class="approval-detail-card">
    <template #header>
      <div class="card-header">
        <span>{{ title }}</span>
        <el-tag v-if="approval?.status" :type="getStatusTagType(approval.status)" size="small">
          {{ getStatusLabel(approval.status) }}
        </el-tag>
      </div>
    </template>
    
    <el-descriptions :column="2" border>
      <el-descriptions-item label="申请标题" :span="2">{{ approval?.title }}</el-descriptions-item>
      <el-descriptions-item label="变更类型">
        <el-tag size="small">{{ getChangeTypeLabel(approval?.change_type) }}</el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="风险等级">
        <el-tag v-if="approval?.sql_risk_level" :type="getRiskTagType(approval.sql_risk_level)" size="small">
          {{ getRiskLabel(approval.sql_risk_level) }}
        </el-tag>
        <span v-else>-</span>
      </el-descriptions-item>
      <el-descriptions-item label="目标实例">{{ approval?.instance_name }}</el-descriptions-item>
      <el-descriptions-item label="目标数据库">{{ approval?.database_target || '-' }}</el-descriptions-item>
      <el-descriptions-item label="申请人">{{ approval?.requester_name }}</el-descriptions-item>
      <el-descriptions-item label="申请时间">{{ formatTime(approval?.created_at) }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.approver_name" label="审批人">{{ approval?.approver_name }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.approved_at" label="审批时间">{{ formatTime(approval?.approved_at) }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.approve_comment" label="审批意见" :span="2">{{ approval?.approve_comment }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.scheduled_time" label="定时执行">{{ formatTime(approval?.scheduled_time) }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.execute_time" label="执行时间">{{ formatTime(approval?.execute_time) }}</el-descriptions-item>
      <el-descriptions-item v-if="approval?.execute_result" label="执行结果" :span="2">{{ approval?.execute_result }}</el-descriptions-item>
    </el-descriptions>
    
    <!-- SQL内容 -->
    <div class="section-title">变更SQL</div>
    <SqlViewer
      title="变更SQL"
      :sql="approval?.sql_content || ''"
      :risk-level="approval?.sql_risk_level"
      :preview-lines="30"
    />
    
    <!-- 回滚SQL -->
    <template v-if="showRollback && approval?.rollback_sql">
      <div class="section-title">
        回滚SQL
        <el-tag v-if="approval?.rollback_generated" type="success" size="small" style="margin-left: 8px;">
          已生成
        </el-tag>
      </div>
      <SqlViewer
        title="回滚SQL"
        :sql="approval.rollback_sql"
        :preview-lines="20"
      />
    </template>
  </el-card>
</template>

<script setup>
import SqlViewer from './SqlViewer.vue'
import dayjs from 'dayjs'

const props = defineProps({
  title: {
    type: String,
    default: '审批详情'
  },
  approval: {
    type: Object,
    default: () => ({})
  },
  showRollback: {
    type: Boolean,
    default: true
  }
})

const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

const getStatusTagType = (status) => {
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

const getChangeTypeLabel = (type) => {
  const labels = {
    DDL: 'DDL变更',
    DML: 'DML变更',
    OPERATION: '运维操作',
    CUSTOM: '自定义'
  }
  return labels[type] || type
}

const getRiskTagType = (level) => {
  const types = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger'
  }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '极高风险'
  }
  return labels[level] || level
}
</script>

<style scoped>
.approval-detail-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-title {
  margin: 20px 0 12px;
  font-size: 15px;
  font-weight: 500;
  color: var(--el-text-color-primary);
}
</style>
