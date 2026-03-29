<template>
  <div class="redis-detail">
    <el-page-header @back="goBack" title="返回">
      <template #content>
        <span class="instance-title">{{ instance?.name }}</span>
        <el-tag :type="connectionStatus === 'connected' ? 'success' : 'danger'" size="small">
          {{ connectionStatus === 'connected' ? '在线' : '离线' }}
        </el-tag>
        <el-tag v-if="redisInfo?.server?.version" type="info" size="small" style="margin-left: 8px;">
          Redis {{ redisInfo?.server?.version }}
        </el-tag>
      </template>
    </el-page-header>
    
    <!-- 概览卡片 -->
    <div class="overview-cards">
      <el-row :gutter="16">
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-icon memory">
              <el-icon><Coin /></el-icon>
            </div>
            <div class="metric-content">
              <div class="metric-label">内存使用</div>
              <div class="metric-value">{{ redisInfo?.memory?.used_memory_human || '-' }}</div>
              <div class="metric-sub">峰值: {{ redisInfo?.memory?.used_memory_peak_human || '-' }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-icon keys">
              <el-icon><Key /></el-icon>
            </div>
            <div class="metric-content">
              <div class="metric-label">键数量</div>
              <div class="metric-value">{{ redisInfo?.db_size || 0 }}</div>
              <div class="metric-sub">碎片率: {{ redisInfo?.memory?.mem_fragmentation_ratio || '-' }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-icon ops">
              <el-icon><Lightning /></el-icon>
            </div>
            <div class="metric-content">
              <div class="metric-label">OPS</div>
              <div class="metric-value">{{ redisInfo?.stats?.instantaneous_ops_per_sec || 0 }}</div>
              <div class="metric-sub">总命令: {{ formatNumber(redisInfo?.stats?.total_commands_processed) }}</div>
            </div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="metric-card">
            <div class="metric-icon clients">
              <el-icon><User /></el-icon>
            </div>
            <div class="metric-content">
              <div class="metric-label">客户端连接</div>
              <div class="metric-value">{{ redisInfo?.clients?.connected_clients || 0 }}</div>
              <div class="metric-sub">阻塞: {{ redisInfo?.clients?.blocked_clients || 0 }}</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </div>
    
    <el-tabs v-model="activeTab" class="detail-tabs">
      <!-- 键管理 -->
      <el-tab-pane label="键管理" name="keys">
        <div class="keys-section">
          <div class="keys-toolbar">
            <el-input
              v-model="keyPattern"
              placeholder="搜索键（支持通配符 * ?）"
              prefix-icon="Search"
              style="width: 300px;"
              clearable
              @keyup.enter="handleScanKeys"
            >
              <template #append>
                <el-button @click="handleScanKeys">搜索</el-button>
              </template>
            </el-input>
            <el-button type="primary" @click="showAddKeyDialog = true" v-if="canOperate">
              <el-icon><Plus /></el-icon>
              添加键
            </el-button>
          </div>
          
          <el-table
            :data="keyList"
            style="width: 100%"
            v-loading="keysLoading"
            @row-click="handleKeyClick"
            highlight-current-row
            class="keys-table"
          >
            <el-table-column prop="key" label="键名" min-width="150" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="getTypeTagType(row.type)">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="length" label="长度" width="80" align="right" />
            <el-table-column prop="ttl_human" label="TTL" width="100" align="center" />
            <el-table-column label="操作" min-width="160" fixed="right" align="center">
              <template #default="{ row }">
                <div class="table-operations">
                  <el-button link type="primary" size="small" @click.stop="viewKeyDetail(row)">查看</el-button>
                  <el-button link type="warning" size="small" @click.stop="editTTL(row)" v-if="canOperate">TTL</el-button>
                  <el-button link type="danger" size="small" @click.stop="deleteKey(row)" v-if="canOperate">删除</el-button>
                </div>
              </template>
            </el-table-column>
          </el-table>
          
          <div class="keys-pagination" v-if="keyList.length > 0">
            <el-button
              :disabled="scanCursor === 0 || !hasMoreKeys"
              @click="loadMoreKeys"
            >
              加载更多
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 服务器信息 -->
      <el-tab-pane label="服务器信息" name="server">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="Redis版本">{{ redisInfo?.server?.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行模式">{{ redisInfo?.server?.mode || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作系统">{{ redisInfo?.server?.os || '-' }}</el-descriptions-item>
          <el-descriptions-item label="架构">{{ redisInfo?.server?.arch_bits || '-' }}位</el-descriptions-item>
          <el-descriptions-item label="进程ID">{{ redisInfo?.server?.process_id || '-' }}</el-descriptions-item>
          <el-descriptions-item label="端口">{{ redisInfo?.server?.tcp_port || '-' }}</el-descriptions-item>
          <el-descriptions-item label="运行时间">{{ formatUptime(redisInfo?.server?.uptime_in_seconds) }}</el-descriptions-item>
          <el-descriptions-item label="配置文件">{{ redisInfo?.server?.config_file || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      
      <!-- 内存信息 -->
      <el-tab-pane label="内存信息" name="memory">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="已使用内存">{{ redisInfo?.memory?.used_memory_human || '-' }}</el-descriptions-item>
          <el-descriptions-item label="RSS内存">{{ redisInfo?.memory?.used_memory_rss_human || '-' }}</el-descriptions-item>
          <el-descriptions-item label="峰值内存">{{ redisInfo?.memory?.used_memory_peak_human || '-' }}</el-descriptions-item>
          <el-descriptions-item label="系统总内存">{{ redisInfo?.memory?.total_system_memory_human || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最大内存限制">{{ redisInfo?.memory?.maxmemory_human || '未设置' }}</el-descriptions-item>
          <el-descriptions-item label="内存策略">{{ redisInfo?.memory?.maxmemory_policy || '-' }}</el-descriptions-item>
          <el-descriptions-item label="内存碎片率">{{ redisInfo?.memory?.mem_fragmentation_ratio || '-' }}</el-descriptions-item>
          <el-descriptions-item label="内存分配器">{{ redisInfo?.memory?.mem_allocator || '-' }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      
      <!-- 统计信息 -->
      <el-tab-pane label="统计信息" name="stats">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="总连接数">{{ formatNumber(redisInfo?.stats?.total_connections_received) }}</el-descriptions-item>
          <el-descriptions-item label="总命令数">{{ formatNumber(redisInfo?.stats?.total_commands_processed) }}</el-descriptions-item>
          <el-descriptions-item label="当前OPS">{{ redisInfo?.stats?.instantaneous_ops_per_sec || 0 }}</el-descriptions-item>
          <el-descriptions-item label="键命中率">{{ getKeyspaceHitRate() }}%</el-descriptions-item>
          <el-descriptions-item label="输入流量">{{ formatBytes(redisInfo?.stats?.total_net_input_bytes) }}</el-descriptions-item>
          <el-descriptions-item label="输出流量">{{ formatBytes(redisInfo?.stats?.total_net_output_bytes) }}</el-descriptions-item>
          <el-descriptions-item label="拒绝连接数">{{ redisInfo?.stats?.rejected_connections || 0 }}</el-descriptions-item>
          <el-descriptions-item label="过期键数">{{ redisInfo?.stats?.expired_keys || 0 }}</el-descriptions-item>
          <el-descriptions-item label="驱逐键数">{{ redisInfo?.stats?.evicted_keys || 0 }}</el-descriptions-item>
          <el-descriptions-item label="缓存命中">{{ formatNumber(redisInfo?.stats?.keyspace_hits) }}</el-descriptions-item>
          <el-descriptions-item label="缓存未命中">{{ formatNumber(redisInfo?.stats?.keyspace_misses) }}</el-descriptions-item>
        </el-descriptions>
      </el-tab-pane>
      
      <!-- 慢查询日志 -->
      <el-tab-pane label="慢查询日志" name="slowlog">
        <el-table :data="slowlogList" style="width: 100%" v-loading="slowlogLoading">
          <el-table-column prop="id" label="ID" width="100" />
          <el-table-column prop="start_time" label="执行时间" width="180" />
          <el-table-column prop="duration_us" label="耗时(μs)" width="120">
            <template #default="{ row }">
              <el-tag :type="row.duration_us > 10000 ? 'danger' : row.duration_us > 1000 ? 'warning' : 'success'">
                {{ row.duration_us }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="command" label="命令" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
      
      <!-- 客户端列表 -->
      <el-tab-pane label="客户端列表" name="clients">
        <el-table :data="clientList" style="width: 100%" v-loading="clientsLoading" max-height="500">
          <el-table-column prop="addr" label="地址" width="200" />
          <el-table-column prop="name" label="名称" width="150" />
          <el-table-column prop="age" label="连接时长(秒)" width="120" />
          <el-table-column prop="idle" label="空闲时长(秒)" width="120" />
          <el-table-column prop="flags" label="标志" width="100" />
          <el-table-column prop="db" label="数据库" width="80" />
          <el-table-column prop="sub" label="订阅数" width="80" />
          <el-table-column prop="psub" label="模式订阅" width="80" />
        </el-table>
      </el-tab-pane>
      
      <!-- 配置查看 -->
      <el-tab-pane label="配置" name="config">
        <el-input
          v-model="configSearch"
          placeholder="搜索配置项"
          prefix-icon="Search"
          style="margin-bottom: 16px; width: 300px;"
          clearable
        />
        <el-table :data="filteredConfig" style="width: 100%" max-height="500">
          <el-table-column prop="name" label="配置项" width="300" />
          <el-table-column prop="value" label="值" show-overflow-tooltip />
        </el-table>
      </el-tab-pane>
    </el-tabs>
    
    <!-- 键详情对话框 -->
    <el-dialog v-model="keyDetailDialog" :title="`键详情: ${selectedKey?.key}`" width="600px">
      <el-descriptions :column="1" border v-if="keyDetail">
        <el-descriptions-item label="类型">{{ keyDetail.info?.type }}</el-descriptions-item>
        <el-descriptions-item label="TTL">{{ keyDetail.info?.ttl_human }}</el-descriptions-item>
        <el-descriptions-item label="长度">{{ keyDetail.info?.length }}</el-descriptions-item>
        <el-descriptions-item label="值">
          <div class="key-value">{{ keyDetail.value }}</div>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
    
    <!-- 添加键对话框 -->
    <el-dialog v-model="showAddKeyDialog" title="添加键" width="500px">
      <el-form :model="newKeyForm" label-width="80px">
        <el-form-item label="键名">
          <el-input v-model="newKeyForm.key" placeholder="请输入键名" />
        </el-form-item>
        <el-form-item label="值">
          <el-input v-model="newKeyForm.value" type="textarea" :rows="4" placeholder="请输入值" />
        </el-form-item>
        <el-form-item label="TTL(秒)">
          <el-input-number v-model="newKeyForm.ttl" :min="0" placeholder="留空表示永不过期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddKeyDialog = false">取消</el-button>
        <el-button type="primary" @click="addKey">确定</el-button>
      </template>
    </el-dialog>
    
    <!-- 设置TTL对话框 -->
    <el-dialog v-model="showTTlDialog" title="设置TTL" width="400px">
      <el-form label-width="80px">
        <el-form-item label="键名">
          <el-input :value="selectedKey?.key" disabled />
        </el-form-item>
        <el-form-item label="TTL(秒)">
          <el-input-number v-model="newTTL" :min="-1" placeholder="-1表示永不过期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showTTlDialog = false">取消</el-button>
        <el-button type="primary" @click="setTTL">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Coin, Key, Lightning, User, Plus } from '@element-plus/icons-vue'
import { instancesApi } from '@/api/instances'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

// 操作权限：管理员和运维人员可以操作
const canOperate = computed(() => userStore.canOperate)

const instanceId = computed(() => route.params.id)
const instance = ref(null)
const connectionStatus = ref('disconnected')
const activeTab = ref('keys')
const redisInfo = ref(null)

// 键管理
const keyPattern = ref('*')
const keyList = ref([])
const keysLoading = ref(false)
const scanCursor = ref(0)
const hasMoreKeys = ref(false)
const selectedKey = ref(null)
const keyDetailDialog = ref(false)
const keyDetail = ref(null)

// 添加键
const showAddKeyDialog = ref(false)
const newKeyForm = ref({
  key: '',
  value: '',
  ttl: null
})

// 设置TTL
const showTTlDialog = ref(false)
const newTTL = ref(-1)

// 慢查询日志
const slowlogList = ref([])
const slowlogLoading = ref(false)

// 客户端列表
const clientList = ref([])
const clientsLoading = ref(false)

// 配置
const redisConfig = ref({})
const configSearch = ref('')

const filteredConfig = computed(() => {
  if (!configSearch.value) {
    return Object.entries(redisConfig.value).map(([name, value]) => ({ name, value }))
  }
  const search = configSearch.value.toLowerCase()
  return Object.entries(redisConfig.value)
    .filter(([name]) => name.toLowerCase().includes(search))
    .map(([name, value]) => ({ name, value }))
})

// 返回上一页
const goBack = () => {
  router.push('/instances')
}

// 格式化数字
const formatNumber = (num) => {
  if (!num) return '0'
  return num.toLocaleString()
}

// 格式化字节
const formatBytes = (bytes) => {
  if (!bytes) return '0B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return `${bytes.toFixed(2)} ${units[i]}`
}

// 格式化运行时间
const formatUptime = (seconds) => {
  if (!seconds) return '-'
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${days}天 ${hours}小时 ${minutes}分钟`
}

// 计算键命中率
const getKeyspaceHitRate = () => {
  const hits = redisInfo.value?.stats?.keyspace_hits || 0
  const misses = redisInfo.value?.stats?.keyspace_misses || 0
  const total = hits + misses
  if (total === 0) return '0.00'
  return ((hits / total) * 100).toFixed(2)
}

// 获取类型标签样式
const getTypeTagType = (type) => {
  const typeMap = {
    string: 'primary',
    list: 'success',
    set: 'warning',
    zset: 'danger',
    hash: 'info'
  }
  return typeMap[type] || ''
}

// 获取实例详情
const fetchInstance = async () => {
  try {
    instance.value = await instancesApi.getDetail(instanceId.value)
  } catch (error) {
    console.error('获取实例详情失败:', error)
  }
}

// 获取 Redis 信息
const fetchRedisInfo = async () => {
  try {
    const result = await request.get(`/redis/${instanceId.value}/info`)
    redisInfo.value = result
    connectionStatus.value = 'connected'
  } catch (error) {
    console.error('获取Redis信息失败:', error)
    connectionStatus.value = 'disconnected'
  }
}

// 扫描键
const handleScanKeys = async () => {
  scanCursor.value = 0
  keyList.value = []
  await loadMoreKeys()
}

const loadMoreKeys = async () => {
  keysLoading.value = true
  try {
    const result = await request.get(`/redis/${instanceId.value}/keys`, {
      params: {
        pattern: keyPattern.value || '*',
        cursor: scanCursor.value,
        count: 100
      }
    })
    keyList.value = [...keyList.value, ...result.keys]
    scanCursor.value = result.cursor
    hasMoreKeys.value = result.has_more
  } catch (error) {
    console.error('扫描键失败:', error)
  } finally {
    keysLoading.value = false
  }
}

// 点击键行
const handleKeyClick = (row) => {
  viewKeyDetail(row)
}

// 查看键详情
const viewKeyDetail = async (row) => {
  try {
    const result = await request.get(`/redis/${instanceId.value}/keys/${encodeURIComponent(row.key)}`)
    keyDetail.value = result
    selectedKey.value = row
    keyDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取键详情失败')
  }
}

// 编辑TTL
const editTTL = (row) => {
  selectedKey.value = row
  newTTL.value = row.ttl || -1
  showTTlDialog.value = true
}

// 设置TTL
const setTTL = async () => {
  try {
    await request.put(`/redis/${instanceId.value}/keys/ttl`, {
      key: selectedKey.value.key,
      ttl: newTTL.value
    })
    ElMessage.success('设置成功')
    showTTlDialog.value = false
    handleScanKeys()
  } catch (error) {
    ElMessage.error('设置失败')
  }
}

// 删除键
const deleteKey = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除键 "${row.key}" 吗？`, '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/redis/${instanceId.value}/keys/${encodeURIComponent(row.key)}`)
    ElMessage.success('删除成功')
    handleScanKeys()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 添加键
const addKey = async () => {
  if (!newKeyForm.value.key) {
    ElMessage.warning('请输入键名')
    return
  }
  try {
    await request.post(`/redis/${instanceId.value}/keys`, newKeyForm.value)
    ElMessage.success('添加成功')
    showAddKeyDialog.value = false
    newKeyForm.value = { key: '', value: '', ttl: null }
    handleScanKeys()
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

// 获取慢查询日志
const fetchSlowlog = async () => {
  slowlogLoading.value = true
  try {
    slowlogList.value = await request.get(`/redis/${instanceId.value}/slowlog`, {
      params: { limit: 50 }
    })
  } catch (error) {
    console.error('获取慢查询日志失败:', error)
  } finally {
    slowlogLoading.value = false
  }
}

// 获取客户端列表
const fetchClients = async () => {
  clientsLoading.value = true
  try {
    clientList.value = await request.get(`/redis/${instanceId.value}/clients`)
  } catch (error) {
    console.error('获取客户端列表失败:', error)
  } finally {
    clientsLoading.value = false
  }
}

// 获取配置
const fetchConfig = async () => {
  try {
    redisConfig.value = await request.get(`/redis/${instanceId.value}/config`)
  } catch (error) {
    console.error('获取配置失败:', error)
  }
}

// 刷新定时器
let refreshTimer = null

const startRefresh = () => {
  refreshTimer = setInterval(() => {
    if (activeTab.value === 'keys' && keyList.value.length > 0) {
      // 不自动刷新键列表，避免影响浏览
    } else if (activeTab.value === 'slowlog') {
      fetchSlowlog()
    } else if (activeTab.value === 'clients') {
      fetchClients()
    }
  }, 30000)
}

// 监听 tab 切换，懒加载数据
watch(activeTab, (newTab) => {
  if (newTab === 'slowlog' && slowlogList.value.length === 0) {
    fetchSlowlog()
  } else if (newTab === 'clients' && clientList.value.length === 0) {
    fetchClients()
  } else if (newTab === 'server' && !redisInfo.value?.server) {
    fetchRedisInfo()
  } else if (newTab === 'config' && Object.keys(redisConfig.value).length === 0) {
    fetchConfig()
  }
})

onMounted(async () => {
  await fetchInstance()
  await fetchRedisInfo()
  await handleScanKeys()
  startRefresh()
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
  }
})
</script>

<style scoped>
.redis-detail {
  padding: 20px;
}

.instance-title {
  margin-right: 12px;
  font-weight: 600;
}

.overview-cards {
  margin: 20px 0;
}

.metric-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: var(--el-box-shadow-light);
}

.metric-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
  color: white;
}

.metric-icon.memory {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.metric-icon.keys {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.metric-icon.ops {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.metric-icon.clients {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.metric-content {
  flex: 1;
}

.metric-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}

.metric-value {
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.metric-sub {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
}

.detail-tabs {
  margin-top: 20px;
}

.keys-section {
  padding: 20px 0;
}

.keys-toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 16px;
}

.keys-table {
  cursor: pointer;
}

.keys-pagination {
  margin-top: 16px;
  text-align: center;
}

.key-value {
  max-height: 300px;
  overflow: auto;
  padding: 10px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
  font-family: monospace;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
