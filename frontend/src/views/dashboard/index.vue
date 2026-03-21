<template>
  <div class="dashboard">
    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stat-cards">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #1890ff;">
            <el-icon :size="24"><Server /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.instanceCount }}</div>
            <div class="stat-label">数据库实例</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #52c41a;">
            <el-icon :size="24"><Connection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.onlineCount }}</div>
            <div class="stat-label">在线实例</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #faad14;">
            <el-icon :size="24"><Stamp /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.pendingApprovalCount }}</div>
            <div class="stat-label">待审批</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon" style="background: #ff4d4f;">
            <el-icon :size="24"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.alertCount }}</div>
            <div class="stat-label">告警</div>
          </div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 性能概览 -->
    <el-card class="performance-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>实例性能概览</span>
          <el-button text @click="refreshPerformance">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-table :data="performanceData" style="width: 100%">
        <el-table-column label="实例" width="200">
          <template #default="{ row }">
            <div class="instance-info">
              <span class="instance-name">{{ row.instance_name }}</span>
              <span
                v-if="row.environment"
                class="env-tag"
                :class="row.environment_code"
                :style="{ backgroundColor: row.environment_color }"
              >
                {{ row.environment }}
              </span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="监控状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.monitor_enabled ? 'success' : 'info'" size="small">
              {{ row.monitor_enabled ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="CPU使用率" width="180">
          <template #default="{ row }">
            <div v-if="row.current_cpu !== null" class="progress-wrapper">
              <el-progress
                :percentage="row.current_cpu"
                :color="getProgressColor(row.current_cpu)"
                :stroke-width="12"
              />
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="内存使用率" width="180">
          <template #default="{ row }">
            <div v-if="row.current_memory !== null" class="progress-wrapper">
              <el-progress
                :percentage="row.current_memory"
                :color="getProgressColor(row.current_memory)"
                :stroke-width="12"
              />
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="连接数" width="100">
          <template #default="{ row }">
            <span>{{ row.current_connections || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="QPS" width="100">
          <template #default="{ row }">
            <span>{{ row.current_qps ? row.current_qps.toFixed(0) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="采集时间" width="180">
          <template #default="{ row }">
            <span v-if="row.collect_time">{{ formatTime(row.collect_time) }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" fixed="right" width="100">
          <template #default="{ row }">
            <el-button text type="primary" @click="viewInstance(row.instance_id)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 待办事项 -->
    <el-card class="todo-card" shadow="never">
      <template #header>
        <span>待办事项</span>
      </template>
      
      <el-empty v-if="todoList.length === 0" description="暂无待办事项" />
      <div v-else class="todo-list">
        <div v-for="item in todoList" :key="item.id" class="todo-item">
          <div class="todo-content">
            <el-tag :type="getTodoType(item.type)" size="small">
              {{ item.typeLabel }}
            </el-tag>
            <span class="todo-title">{{ item.title }}</span>
          </div>
          <el-button text type="primary" size="small" @click="handleTodo(item)">
            {{ item.actionLabel }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { monitorApi } from '@/api/monitor'
import dayjs from 'dayjs'

const router = useRouter()

const stats = reactive({
  instanceCount: 0,
  onlineCount: 0,
  pendingApprovalCount: 0,
  alertCount: 0
})

const performanceData = ref([])
const todoList = ref([])

// 刷新性能数据
const refreshPerformance = async () => {
  try {
    const data = await monitorApi.performance.getOverview()
    performanceData.value = data
    
    // 更新统计
    stats.instanceCount = data.length
    stats.onlineCount = data.filter(d => d.monitor_enabled).length
  } catch (error) {
    console.error('获取性能概览失败:', error)
  }
}

// 获取进度条颜色
const getProgressColor = (value) => {
  if (value >= 80) return '#ff4d4f'
  if (value >= 60) return '#faad14'
  return '#52c41a'
}

// 格式化时间
const formatTime = (time) => {
  return dayjs(time).format('MM-DD HH:mm:ss')
}

// 查看实例详情
const viewInstance = (id) => {
  router.push(`/instances/${id}`)
}

// 获取待办类型
const getTodoType = (type) => {
  const types = {
    approval: 'warning',
    alert: 'danger'
  }
  return types[type] || 'info'
}

// 处理待办
const handleTodo = (item) => {
  router.push(item.path)
}

onMounted(() => {
  refreshPerformance()
})
</script>

<style lang="scss" scoped>
.dashboard {
  .stat-cards {
    margin-bottom: 20px;
    
    .stat-card {
      background: #fff;
      border-radius: 8px;
      padding: 20px;
      display: flex;
      align-items: center;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
      
      .stat-icon {
        width: 56px;
        height: 56px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        margin-right: 16px;
      }
      
      .stat-info {
        .stat-value {
          font-size: 28px;
          font-weight: bold;
          color: #333;
        }
        
        .stat-label {
          font-size: 14px;
          color: #999;
          margin-top: 4px;
        }
      }
    }
  }
  
  .performance-card {
    margin-bottom: 20px;
    
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .instance-info {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .instance-name {
        font-weight: 500;
      }
    }
    
    .progress-wrapper {
      width: 120px;
    }
    
    .text-muted {
      color: #999;
    }
  }
  
  .todo-card {
    .todo-list {
      .todo-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 0;
        border-bottom: 1px solid #f0f0f0;
        
        &:last-child {
          border-bottom: none;
        }
        
        .todo-content {
          display: flex;
          align-items: center;
          gap: 12px;
          
          .todo-title {
            color: #333;
          }
        }
      }
    }
  }
}
</style>
