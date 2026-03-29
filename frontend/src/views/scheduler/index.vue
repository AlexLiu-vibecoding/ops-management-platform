<template>
  <div class="scheduler-page">
    <!-- 调度器状态概览 -->
    <el-row :gutter="20" class="status-row">
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-header">
            <el-icon class="status-icon" :class="{ running: overview.approval_scheduler?.is_running }">
              <Timer />
            </el-icon>
            <div class="status-info">
              <div class="status-title">{{ overview.approval_scheduler?.name || '审批调度器' }}</div>
              <div class="status-badge">
                <el-tag :type="overview.approval_scheduler?.is_running ? 'success' : 'danger'" size="small">
                  {{ overview.approval_scheduler?.is_running ? '运行中' : '已停止' }}
                </el-tag>
                <span class="job-count">{{ overview.approval_scheduler?.job_count || 0 }} 个任务</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-header">
            <el-icon class="status-icon" :class="{ running: overview.task_scheduler?.is_running }">
              <Setting />
            </el-icon>
            <div class="status-info">
              <div class="status-title">{{ overview.task_scheduler?.name || '任务调度器' }}</div>
              <div class="status-badge">
                <el-tag :type="overview.task_scheduler?.is_running ? 'success' : 'danger'" size="small">
                  {{ overview.task_scheduler?.is_running ? '运行中' : '已停止' }}
                </el-tag>
                <span class="job-count">{{ overview.task_scheduler?.job_count || 0 }} 个任务</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover" class="status-card summary-card">
          <div class="status-header">
            <el-icon class="status-icon running">
              <DataAnalysis />
            </el-icon>
            <div class="status-info">
              <div class="status-title">任务统计</div>
              <div class="summary-stats">
                <div class="stat-item">
                  <span class="stat-label">总数</span>
                  <span class="stat-value">{{ overview.total_jobs || 0 }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label running">运行</span>
                  <span class="stat-value running">{{ overview.running_jobs || 0 }}</span>
                </div>
                <div class="stat-item">
                  <span class="stat-label paused">暂停</span>
                  <span class="stat-value paused">{{ overview.paused_jobs || 0 }}</span>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 任务列表 -->
    <el-card shadow="never" class="jobs-card">
      <template #header>
        <div class="card-header">
          <span>后台任务列表</span>
          <el-button type="primary" :icon="Refresh" @click="fetchOverview">刷新状态</el-button>
        </div>
      </template>
      
      <el-table :data="jobs" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="任务ID" width="200" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="job-id">{{ row.id }}</code>
          </template>
        </el-table-column>
        
        <el-table-column prop="name" label="任务名称" min-width="150">
          <template #default="{ row }">
            <div class="job-name">
              <span>{{ row.name }}</span>
              <span v-if="row.description" class="job-desc">{{ row.description }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="task_type" label="类型" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getTaskTypeStyle(row.task_type)" size="small">
              {{ getTaskTypeLabel(row.task_type) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="trigger_type" label="触发方式" width="120">
          <template #default="{ row }">
            <div class="trigger-info">
              <el-tag size="small" effect="plain">{{ getTriggerTypeLabel(row.trigger_type) }}</el-tag>
              <span class="trigger-config">{{ row.trigger_config }}</span>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column prop="next_run_time" label="下次执行时间" width="180">
          <template #default="{ row }">
            <span v-if="row.next_run_time">{{ formatTime(row.next_run_time) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'running' ? 'success' : row.status === 'paused' ? 'warning' : 'info'" size="small">
              {{ row.status === 'running' ? '运行中' : row.status === 'paused' ? '已暂停' : '待执行' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="handler" label="处理器" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <code class="handler-name">{{ row.handler || '-' }}</code>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" min-width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="table-operations">
              <el-button 
                v-if="row.status === 'running'" 
                link 
                type="warning" 
                size="small" 
                @click="handleJobAction(row, 'pause')"
                :loading="row._actionLoading"
              >
                暂停
              </el-button>
              <el-button 
                v-if="row.status === 'paused'" 
                link 
                type="success" 
                size="small" 
                @click="handleJobAction(row, 'resume')"
                :loading="row._actionLoading"
              >
                恢复
              </el-button>
              <el-button 
                link 
                type="primary" 
                size="small" 
                @click="handleJobAction(row, 'trigger')"
                :loading="row._actionLoading"
              >
                立即执行
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 任务说明 -->
    <el-card shadow="never" class="info-card">
      <template #header>
        <div class="card-header">
          <el-icon><InfoFilled /></el-icon>
          <span>任务说明</span>
        </div>
      </template>
      
      <div class="task-descriptions">
        <div class="task-desc-item">
          <h4>审批调度器 (Approval Scheduler)</h4>
          <ul>
            <li><code>check_scheduled_approvals</code> - 每分钟检查需要定时执行的审批工单</li>
            <li><code>cleanup_expired_files</code> - 每天凌晨2点清理过期的SQL文件</li>
            <li><code>approval_execute_*</code> - 用户创建的定时执行审批工单任务</li>
          </ul>
        </div>
        
        <div class="task-desc-item">
          <h4>任务调度器 (Task Scheduler)</h4>
          <ul>
            <li><code>rds_performance_collector</code> - 每5分钟采集RDS实例性能指标</li>
            <li><code>scheduled_task_*</code> - 用户自定义的定时脚本任务</li>
          </ul>
        </div>
        
        <div class="task-desc-item warning">
          <h4><el-icon><WarningFilled /></el-icon> 注意事项</h4>
          <ul>
            <li>暂停/恢复操作仅影响定时触发，不会中断正在执行的任务</li>
            <li>立即执行会触发任务立刻运行，请谨慎操作</li>
            <li>系统核心任务建议保持运行状态</li>
          </ul>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Timer, Setting, DataAnalysis, Refresh, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

// 数据
const loading = ref(false)
const overview = ref({
  approval_scheduler: null,
  task_scheduler: null,
  total_jobs: 0,
  running_jobs: 0,
  paused_jobs: 0
})
const jobs = ref([])
let refreshTimer = null

// 获取调度器概览
const fetchOverview = async () => {
  loading.value = true
  try {
    const res = await request.get('/scheduler/overview')
    overview.value = res.data || {}
    jobs.value = res.data?.approval_scheduler?.jobs || []
    // 合并任务调度器的任务
    const taskJobs = res.data?.task_scheduler?.jobs || []
    jobs.value = [...jobs.value, ...taskJobs]
  } catch (error) {
    console.error('获取调度器状态失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取调度器状态失败')
  } finally {
    loading.value = false
  }
}

// 执行任务操作
const handleJobAction = async (job, action) => {
  const actionLabels = {
    pause: '暂停',
    resume: '恢复',
    trigger: '立即执行'
  }
  
  // 立即执行需要确认
  if (action === 'trigger') {
    try {
      await ElMessageBox.confirm(
        `确定要立即执行任务 "${job.name || job.id}" 吗？`,
        '确认执行',
        { type: 'warning' }
      )
    } catch {
      return
    }
  }
  
  job._actionLoading = true
  try {
    await request.post(`/scheduler/jobs/${job.id}/action`, { action })
    ElMessage.success(`任务已${actionLabels[action]}`)
    // 刷新状态
    await fetchOverview()
  } catch (error) {
    console.error('操作失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    job._actionLoading = false
  }
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('YYYY-MM-DD HH:mm:ss')
}

// 获取任务类型样式
const getTaskTypeStyle = (type) => {
  const styles = {
    'approval': 'primary',
    'scheduled': 'success',
    'system': 'warning'
  }
  return styles[type] || 'info'
}

// 获取任务类型标签
const getTaskTypeLabel = (type) => {
  const labels = {
    'approval': '审批',
    'scheduled': '定时',
    'system': '系统'
  }
  return labels[type] || type
}

// 获取触发类型标签
const getTriggerTypeLabel = (type) => {
  const labels = {
    'cron': 'Cron',
    'interval': '间隔',
    'date': '定时'
  }
  return labels[type] || type
}

// 初始化
onMounted(() => {
  fetchOverview()
  // 每30秒自动刷新
  refreshTimer = setInterval(fetchOverview, 30000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.scheduler-page {
  padding: 0;
}

.status-row {
  margin-bottom: 20px;
}

.status-card {
  height: 100%;
}

.status-header {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-icon {
  font-size: 48px;
  color: var(--el-text-color-secondary);
  transition: color 0.3s;
}

.status-icon.running {
  color: var(--el-color-success);
}

.status-info {
  flex: 1;
}

.status-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.job-count {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.summary-card .summary-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
}

.stat-value.running {
  color: var(--el-color-success);
}

.stat-value.paused {
  color: var(--el-color-warning);
}

.jobs-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header .el-icon {
  margin-right: 8px;
}

.job-id {
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
}

.job-name {
  display: flex;
  flex-direction: column;
}

.job-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.trigger-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trigger-config {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.handler-name {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color-lighter);
  padding: 2px 6px;
  border-radius: 4px;
}

.text-muted {
  color: var(--el-text-color-placeholder);
}

.table-operations {
  display: flex;
  gap: 8px;
}

.info-card {
  background: var(--el-bg-color-page);
}

.task-descriptions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.task-desc-item {
  padding: 16px;
  background: var(--el-bg-color);
  border-radius: 8px;
}

.task-desc-item h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: var(--el-text-color-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-desc-item ul {
  margin: 0;
  padding-left: 20px;
}

.task-desc-item li {
  margin-bottom: 8px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.task-desc-item li code {
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.task-desc-item.warning {
  border: 1px solid var(--el-color-warning-light-5);
  background: var(--el-color-warning-light-9);
}

.task-desc-item.warning h4 {
  color: var(--el-color-warning);
}
</style>
