<template>
  <div class="dashboard-ios">
    <!-- 页面标题区 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">仪表盘</h1>
          <p class="page-subtitle">欢迎回来，{{ userName }}</p>
        </div>
        <div class="header-right">
          <button class="refresh-btn" @click="refreshAll" :disabled="loading">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6M1 20v-6h6"/>
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
            </svg>
            <span>刷新</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card gradient-blue">
        <div class="stat-card-content">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <line x1="8" y1="21" x2="16" y2="21"/>
              <line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.instanceCount }}</div>
            <div class="stat-label">数据库实例</div>
          </div>
        </div>
        <div class="stat-decoration"></div>
      </div>

      <div class="stat-card gradient-green">
        <div class="stat-card-content">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.onlineCount }}</div>
            <div class="stat-label">在线实例</div>
          </div>
        </div>
        <div class="stat-decoration"></div>
      </div>

      <div class="stat-card gradient-orange">
        <div class="stat-card-content">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
              <polyline points="10 9 9 9 8 9"/>
            </svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.pendingApprovalCount }}</div>
            <div class="stat-label">待审批</div>
          </div>
        </div>
        <div class="stat-decoration"></div>
      </div>

      <div class="stat-card gradient-red">
        <div class="stat-card-content">
          <div class="stat-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ animatedStats.alertCount }}</div>
            <div class="stat-label">告警</div>
          </div>
        </div>
        <div class="stat-decoration"></div>
      </div>
    </div>

    <!-- 性能概览卡片 -->
    <div class="performance-section">
      <div class="section-header">
        <h2 class="section-title">实例性能概览</h2>
        <div class="section-actions">
          <span class="last-update">{{ lastUpdateTime }}</span>
        </div>
      </div>

      <div class="performance-grid">
        <div 
          v-for="item in performanceData" 
          :key="item.instance_id" 
          class="performance-card"
          @click="viewInstance(item.instance_id)"
        >
          <div class="card-header">
            <div class="instance-name">{{ item.instance_name }}</div>
            <span 
              class="env-badge" 
              :style="{ backgroundColor: item.environment_color || '#666' }"
            >
              {{ item.environment }}
            </span>
          </div>
          
          <div class="card-status">
            <span class="status-dot" :class="{ active: item.monitor_enabled }"></span>
            <span class="status-text">
              {{ item.monitor_enabled ? '已启用' : '已禁用' }}
            </span>
          </div>

          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-label">CPU</div>
              <div class="metric-value" v-if="item.current_cpu !== null">
                <span class="metric-number">{{ item.current_cpu.toFixed(1) }}</span>
                <span class="metric-unit">%</span>
              </div>
              <div class="metric-value" v-else>
                <span class="metric-na">-</span>
              </div>
              <div class="metric-bar" v-if="item.current_cpu !== null">
                <div 
                  class="metric-fill" 
                  :style="{ width: `${item.current_cpu}%` }"
                  :class="getMetricClass(item.current_cpu)"
                ></div>
              </div>
            </div>

            <div class="metric-item">
              <div class="metric-label">内存</div>
              <div class="metric-value" v-if="item.current_memory !== null">
                <span class="metric-number">{{ item.current_memory.toFixed(1) }}</span>
                <span class="metric-unit">%</span>
              </div>
              <div class="metric-value" v-else>
                <span class="metric-na">-</span>
              </div>
              <div class="metric-bar" v-if="item.current_memory !== null">
                <div 
                  class="metric-fill" 
                  :style="{ width: `${item.current_memory}%` }"
                  :class="getMetricClass(item.current_memory)"
                ></div>
              </div>
            </div>
          </div>

          <div class="card-footer">
            <div class="footer-stat">
              <span class="footer-label">连接</span>
              <span class="footer-value">{{ item.current_connections || '-' }}</span>
            </div>
            <div class="footer-stat">
              <span class="footer-label">QPS</span>
              <span class="footer-value">{{ item.current_qps ? item.current_qps.toFixed(0) : '-' }}</span>
            </div>
            <div class="footer-stat">
              <span class="footer-label">采集时间</span>
              <span class="footer-value">{{ formatTime(item.collect_time) }}</span>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="performanceData.length === 0 && !loading" class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
            <line x1="8" y1="21" x2="16" y2="21"/>
            <line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <p>暂无数据</p>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-overlay">
      <div class="loading-spinner"></div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { monitorApi } from '@/api/monitor'
import dayjs from 'dayjs'

const router = useRouter()
const userStore = useUserStore()

const loading = ref(false)
const lastUpdateTime = ref('')

const stats = reactive({
  instanceCount: 0,
  onlineCount: 0,
  pendingApprovalCount: 0,
  alertCount: 0
})

const animatedStats = reactive({
  instanceCount: 0,
  onlineCount: 0,
  pendingApprovalCount: 0,
  alertCount: 0
})

const performanceData = ref([])

const userName = computed(() => {
  return userStore.user?.real_name || userStore.user?.username || '用户'
})

// 动画数字
const animateNumber = (target, end, duration = 800) => {
  const start = target.value
  const range = end - start
  const startTime = performance.now()

  const update = (currentTime) => {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const easeOut = 1 - Math.pow(1 - progress, 3)
    
    target.value = Math.round(start + range * easeOut)
    
    if (progress < 1) {
      requestAnimationFrame(update)
    }
  }

  requestAnimationFrame(update)
}

// 刷新所有数据
const refreshAll = async () => {
  loading.value = true
  try {
    await refreshPerformance()
    lastUpdateTime.value = `${dayjs().format('HH:mm:ss')} 已更新`
  } finally {
    loading.value = false
  }
}

// 刷新性能数据
const refreshPerformance = async () => {
  try {
    const data = await monitorApi.performance.getOverview()
    performanceData.value = data
    
    // 更新统计
    const newInstanceCount = data.length
    const newOnlineCount = data.filter(d => d.monitor_enabled).length
    
    // 动画更新数字
    animateNumber({ value: animatedStats.instanceCount }, newInstanceCount)
    animateNumber({ value: animatedStats.onlineCount }, newOnlineCount)
    
    stats.instanceCount = newInstanceCount
    stats.onlineCount = newOnlineCount
  } catch (error) {
    console.error('获取性能概览失败:', error)
  }
}

// 获取指标样式类
const getMetricClass = (value) => {
  if (value >= 80) return 'critical'
  if (value >= 60) return 'warning'
  return 'normal'
}

// 格式化时间
const formatTime = (time) => {
  if (!time) return '-'
  return dayjs(time).format('HH:mm:ss')
}

// 查看实例详情
const viewInstance = (id) => {
  router.push(`/instances/${id}`)
}

onMounted(() => {
  refreshAll()
})
</script>

<style lang="scss" scoped>
// ========================================
// iOS-Style Modern Dashboard
// ========================================

.dashboard-ios {
  position: relative;
  min-height: calc(100vh - 104px);
}

// ========================================
// Page Header
// ========================================
.page-header {
  margin-bottom: 24px;
  
  .header-content {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }
  
  .page-title {
    font-size: 28px;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.5px;
    margin: 0 0 4px 0;
  }
  
  .page-subtitle {
    font-size: 15px;
    color: var(--text-secondary);
    margin: 0;
  }
  
  .refresh-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: var(--glass-bg);
    border: 1px solid var(--separator);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    backdrop-filter: blur(10px);
    
    svg {
      width: 18px;
      height: 18px;
      color: var(--primary);
    }
    
    span {
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
    }
    
    &:hover {
      background: var(--bg-secondary);
      transform: translateY(-1px);
    }
    
    &:disabled {
      opacity: 0.6;
      cursor: not-allowed;
    }
  }
}

// ========================================
// Stats Grid
// ========================================
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  
  @media (max-width: 1200px) {
    grid-template-columns: repeat(2, 1fr);
  }
  
  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
}

.stat-card {
  position: relative;
  padding: 20px;
  border-radius: 16px;
  color: white;
  overflow: hidden;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.15);
  }
  
  &.gradient-blue {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    box-shadow: 0 4px 16px rgba(102, 126, 234, 0.3);
  }
  
  &.gradient-green {
    background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    box-shadow: 0 4px 16px rgba(17, 153, 142, 0.3);
  }
  
  &.gradient-orange {
    background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
    box-shadow: 0 4px 16px rgba(240, 147, 251, 0.3);
  }
  
  &.gradient-red {
    background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    box-shadow: 0 4px 16px rgba(235, 51, 73, 0.3);
  }
  
  .stat-card-content {
    display: flex;
    align-items: center;
    gap: 16px;
    position: relative;
    z-index: 1;
  }
  
  .stat-icon {
    width: 52px;
    height: 52px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    
    svg {
      width: 26px;
      height: 26px;
    }
  }
  
  .stat-info {
    .stat-value {
      font-size: 32px;
      font-weight: 700;
      line-height: 1;
    }
    
    .stat-label {
      font-size: 13px;
      opacity: 0.9;
      margin-top: 4px;
    }
  }
  
  .stat-decoration {
    position: absolute;
    right: -20px;
    bottom: -20px;
    width: 120px;
    height: 120px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 50%;
  }
}

// ========================================
// Performance Section
// ========================================
.performance-section {
  background: var(--glass-bg);
  border-radius: 20px;
  padding: 24px;
  backdrop-filter: blur(10px);
  border: 0.5px solid var(--separator);
  
  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
  }
  
  .section-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }
  
  .last-update {
    font-size: 13px;
    color: var(--text-secondary);
  }
}

// ========================================
// Performance Grid
// ========================================
.performance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
  
  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
}

.performance-card {
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  
  &:hover {
    border-color: var(--primary);
    transform: translateY(-2px);
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .instance-name {
      font-size: 15px;
      font-weight: 600;
      color: var(--text-primary);
    }
    
    .env-badge {
      font-size: 11px;
      padding: 3px 10px;
      border-radius: 20px;
      color: white;
      font-weight: 500;
    }
  }
  
  .card-status {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 16px;
    
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--text-secondary);
      
      &.active {
        background: var(--success);
        box-shadow: 0 0 8px var(--success);
      }
    }
    
    .status-text {
      font-size: 12px;
      color: var(--text-secondary);
    }
  }
  
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }
  
  .metric-item {
    .metric-label {
      font-size: 11px;
      color: var(--text-secondary);
      margin-bottom: 4px;
    }
    
    .metric-value {
      display: flex;
      align-items: baseline;
      gap: 2px;
      margin-bottom: 8px;
      
      .metric-number {
        font-size: 20px;
        font-weight: 600;
        color: var(--text-primary);
      }
      
      .metric-unit {
        font-size: 12px;
        color: var(--text-secondary);
      }
      
      .metric-na {
        font-size: 20px;
        color: var(--text-secondary);
      }
    }
    
    .metric-bar {
      height: 4px;
      background: var(--bg-tertiary);
      border-radius: 2px;
      overflow: hidden;
      
      .metric-fill {
        height: 100%;
        border-radius: 2px;
        transition: width 0.5s ease;
        
        &.normal {
          background: var(--success);
        }
        
        &.warning {
          background: var(--warning);
        }
        
        &.critical {
          background: var(--danger);
        }
      }
    }
  }
  
  .card-footer {
    display: flex;
    justify-content: space-between;
    padding-top: 12px;
    border-top: 1px solid var(--separator);
    
    .footer-stat {
      text-align: center;
      
      .footer-label {
        display: block;
        font-size: 10px;
        color: var(--text-secondary);
        margin-bottom: 2px;
      }
      
      .footer-value {
        font-size: 13px;
        font-weight: 500;
        color: var(--text-primary);
      }
    }
  }
}

// ========================================
// Empty State
// ========================================
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--text-secondary);
  
  svg {
    width: 64px;
    height: 64px;
    margin-bottom: 16px;
    opacity: 0.5;
  }
  
  p {
    margin: 0;
    font-size: 14px;
  }
}

// ========================================
// Loading Overlay
// ========================================
.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 20px;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--separator);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
