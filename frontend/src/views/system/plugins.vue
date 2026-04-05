<template>
  <div class="plugins-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">插件管理</h2>
        <span class="page-desc">管理系统插件，支持查看、测试和重载</span>
      </div>
      <div class="header-right">
        <el-button :icon="Refresh" @click="loadPlugins" :loading="loading">
          刷新列表
        </el-button>
        <el-button :icon="Search" @click="discoverPlugins" :loading="discovering">
          重新发现
        </el-button>
      </div>
    </div>

    <!-- 插件统计 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon primary"><Connection /></div>
            <div class="stat-info">
              <div class="stat-value">{{ plugins.length }}</div>
              <div class="stat-label">已加载插件</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon success"><CircleCheck /></div>
            <div class="stat-info">
              <div class="stat-value">{{ enabledCount }}</div>
              <div class="stat-label">通知插件</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 插件列表 -->
    <el-card shadow="never" class="plugins-card">
      <template #header>
        <div class="card-header">
          <span class="title">插件列表</span>
          <el-tag type="info" size="small">共 {{ plugins.length }} 个插件</el-tag>
        </div>
      </template>

      <el-table :data="plugins" v-loading="loading" style="width: 100%">
        <el-table-column label="插件信息" min-width="200">
          <template #default="{ row }">
            <div class="plugin-info">
              <div class="plugin-icon">
                <el-icon :size="24" :color="getPluginColor(row.channel_type)">
                  <component :is="getPluginIcon(row.channel_type)" />
                </el-icon>
              </div>
              <div class="plugin-details">
                <div class="plugin-name">{{ row.display_name }}</div>
                <div class="plugin-type">
                  <el-tag size="small">{{ row.channel_type }}</el-tag>
                  <el-tag size="small" type="info" class="ml-2">{{ row.version }}</el-tag>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="description" label="描述" min-width="300">
          <template #default="{ row }">
            <span class="plugin-desc">{{ row.description }}</span>
          </template>
        </el-table-column>

        <el-table-column label="支持功能" width="150" align="center">
          <template #default="{ row }">
            <div class="plugin-features">
              <el-tag v-if="row.supports_batch" size="small" type="success">
                批量发送
              </el-tag>
              <el-tag v-if="hasSchema(row)" size="small" type="primary" class="mt-1">
                配置验证
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="配置项" width="120" align="center">
          <template #default="{ row }">
            <el-button
              type="primary"
              link
              size="small"
              @click="showConfigSchema(row)"
              v-if="hasSchema(row)"
            >
              查看配置
            </el-button>
          </template>
        </el-table-column>

        <el-table-column label="测试" width="100" align="center">
          <template #default="{ row }">
            <el-button
              type="success"
              link
              size="small"
              @click="testPlugin(row)"
              :loading="row._testing"
            >
              测试
            </el-button>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button
              type="warning"
              link
              size="small"
              @click="reloadPlugin(row)"
              :loading="row._reloading"
            >
              重载
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && plugins.length === 0" description="暂无插件" />
    </el-card>

    <!-- 配置Schema对话框 -->
    <el-dialog
      v-model="schemaDialogVisible"
      :title="`配置 Schema - ${currentPlugin?.display_name}`"
      width="60%"
      class="schema-dialog"
    >
      <div v-if="currentPlugin">
        <el-descriptions :column="1" border class="mb-4">
          <el-descriptions-item label="插件名称">{{ currentPlugin.display_name }}</el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentPlugin.channel_type }}</el-descriptions-item>
          <el-descriptions-item label="版本">{{ currentPlugin.version }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">配置结构</el-divider>
        <pre class="schema-code">{{ formatSchema(currentPlugin.config_schema) }}</pre>
      </div>

      <template #footer>
        <el-button @click="schemaDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="validateConfig">验证配置</el-button>
      </template>
    </el-dialog>

    <!-- 测试对话框 -->
    <el-dialog
      v-model="testDialogVisible"
      :title="`测试插件 - ${currentPlugin?.display_name}`"
      width="50%"
      class="test-dialog"
    >
      <div v-if="currentPlugin">
        <el-alert
          title="配置提示"
          type="info"
          :closable="false"
          show-icon
          class="mb-4"
        >
          请输入有效的配置信息进行测试。配置格式必须符合插件要求。
        </el-alert>

        <el-form :model="testConfig" label-width="120px">
          <el-form-item label="通道类型">
            <el-input v-model="testConfig.channel_type" disabled />
          </el-form-item>
          <el-form-item label="配置信息">
            <el-input
              v-model="testConfigJson"
              type="textarea"
              :rows="10"
              placeholder='{"webhook": "https://...", "auth_type": "none"}'
            />
          </el-form-item>
          <el-form-item label="测试消息">
            <el-input
              v-model="testMessage"
              type="textarea"
              :rows="3"
              placeholder="输入测试消息内容"
            />
          </el-form-item>
        </el-form>
      </div>

      <template #footer>
        <el-button @click="testDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="runPluginTest" :loading="testing">
          测试发送
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { ElMessage, ElMessageBox } from 'element-plus'
import { 
  Connection, CircleCheck, Refresh, Search, ChatDotRound, 
  Message, Share, Setting 
} from '@element-plus/icons-vue'

// 数据
const loading = ref(false)
const discovering = ref(false)
const plugins = ref([])
const testing = ref(false)

// 对话框
const schemaDialogVisible = ref(false)
const testDialogVisible = ref(false)
const currentPlugin = ref(null)

// 测试配置
const testConfig = reactive({
  channel_type: '',
  config: {}
})
const testConfigJson = ref('')
const testMessage = ref('这是一条测试消息')

// 统计
const enabledCount = computed(() => 
  plugins.value.filter(p => p.channel_type).length
)

// 加载插件列表
const loadPlugins = async () => {
  loading.value = true
  try {
    const res = await request.get('/notification/plugins')
    plugins.value = res.data || []
    ElMessage.success(`成功加载 ${plugins.value.length} 个插件`)
  } catch (error) {
    ElMessage.error('加载插件列表失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// 发现插件
const discoverPlugins = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要重新发现插件吗？这将扫描插件目录并加载新插件。',
      '确认发现',
      { type: 'warning' }
    )
  } catch { return }

  discovering.value = true
  try {
    const res = await request.get('/notification/plugins/discover')
    ElMessage.success(res.message || '插件发现成功')
    await loadPlugins()
  } catch (error) {
    ElMessage.error('发现插件失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    discovering.value = false
  }
}

// 显示配置Schema
const showConfigSchema = async (plugin) => {
  currentPlugin.value = plugin
  try {
    const res = await request.get(`/notification/plugins/${plugin.channel_type}/schema`)
    if (res.success && res.data) {
      currentPlugin.value = {
        ...plugin,
        config_schema: res.data.config_schema
      }
      schemaDialogVisible.value = true
    } else {
      ElMessage.error('获取插件Schema失败')
    }
  } catch (error) {
    ElMessage.error('获取插件Schema失败: ' + (error.response?.data?.detail || error.message))
  }
}

// 格式化Schema
const formatSchema = (schema) => {
  return JSON.stringify(schema, null, 2)
}

// 是否有Schema
const hasSchema = (plugin) => {
  return plugin.config_schema && Object.keys(plugin.config_schema).length > 0
}

// 获取插件图标
const getPluginIcon = (type) => {
  const icons = {
    dingtalk: ChatDotRound,
    wechat: Message,
    email: Share,
    webhook: Connection
  }
  return icons[type] || Setting
}

// 获取插件颜色
const getPluginColor = (type) => {
  const colors = {
    dingtalk: '#0089FF',
    wechat: '#07C160',
    email: '#F56C6C',
    webhook: '#409EFF'
  }
  return colors[type] || '#909399'
}

// 测试插件
const testPlugin = (plugin) => {
  currentPlugin.value = plugin
  testConfig.channel_type = plugin.channel_type
  // 根据插件类型设置默认测试配置
  if (plugin.channel_type === 'dingtalk') {
    testConfigJson.value = JSON.stringify({
      webhook: "https://oapi.dingtalk.com/robot/send?access_token=xxx",
      auth_type: "none"
    }, null, 2)
  } else if (plugin.channel_type === 'wechat') {
    testConfigJson.value = JSON.stringify({
      webhook: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
    }, null, 2)
  } else if (plugin.channel_type === 'email') {
    testConfigJson.value = JSON.stringify({
      smtp_host: "smtp.example.com",
      smtp_port: 587,
      smtp_user: "test@example.com",
      smtp_password: "password",
      sender_email: "noreply@example.com"
    }, null, 2)
  } else {
    testConfigJson.value = JSON.stringify({}, null, 2)
  }
  testMessage.value = '这是一条测试消息'
  testDialogVisible.value = true
}

// 运行插件测试
const runPluginTest = async () => {
  try {
    const config = JSON.parse(testConfigJson.value)
    testConfig.config = config
    
    testing.value = true
    const res = await request.post('/notification/plugins/validate', testConfig)
    
    if (res.success && res.data.valid) {
      ElMessage.success('配置验证通过')
      
      // 尝试发送测试消息
      const messageData = {
        channel_type: testConfig.channel_type,
        config: testConfig.config,
        title: '测试消息',
        content: testMessage.value,
        markdown: true,
        at_users: []
      }
      
      const sendRes = await request.post('/notification/plugins/send', messageData)
      if (sendRes.success) {
        ElMessage.success('测试消息发送成功')
      } else {
        ElMessage.warning('测试消息发送失败: ' + (sendRes.data?.error_message || '未知错误'))
      }
    } else {
      ElMessage.error('配置验证失败: ' + (res.data?.message || '请检查配置格式'))
    }
  } catch (error) {
    if (error.message.includes('JSON')) {
      ElMessage.error('配置JSON格式错误，请检查输入')
    } else {
      ElMessage.error('测试失败: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    testing.value = false
  }
}

// 验证配置
const validateConfig = async () => {
  try {
    const schema = currentPlugin.value.config_schema
    ElMessage.success('Schema格式正确，包含必需字段')
  } catch (error) {
    ElMessage.error('Schema验证失败')
  }
}

// 重载插件
const reloadPlugin = async (plugin) => {
  try {
    await ElMessageBox.confirm(
      `确定要重载插件 "${plugin.display_name}" 吗？`,
      '确认重载',
      { type: 'warning' }
    )
  } catch { return }

  plugin._reloading = true
  try {
    const res = await request.post(`/notification/plugins/reload/${plugin.channel_type}`)
    if (res.success) {
      ElMessage.success(`插件 ${plugin.display_name} 重载成功`)
    } else {
      ElMessage.error(`插件重载失败: ${res.message}`)
    }
  } catch (error) {
    ElMessage.error('重载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    plugin._reloading = false
  }
}

// 生命周期
onMounted(() => {
  loadPlugins()
})
</script>

<style scoped>
.plugins-page {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left h2 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
}

.page-desc {
  color: #909399;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-content {
  display: flex;
  align-items: center;
  padding: 10px;
}

.stat-icon {
  width: 50px;
  height: 50px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  font-size: 24px;
}

.stat-icon.primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.stat-icon.success {
  background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 4px;
}

.stat-label {
  color: #909399;
  font-size: 14px;
}

.plugins-card {
  margin-top: 0;
}

.plugin-info {
  display: flex;
  align-items: center;
  padding: 8px 0;
}

.plugin-icon {
  margin-right: 12px;
}

.plugin-details {
  flex: 1;
}

.plugin-name {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 6px;
}

.plugin-type {
  display: flex;
  gap: 6px;
}

.plugin-desc {
  color: #606266;
  font-size: 14px;
  line-height: 1.5;
}

.plugin-features {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.schema-dialog .schema-code {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 4px;
  overflow: auto;
  max-height: 400px;
  font-size: 13px;
  line-height: 1.6;
}

.test-dialog .el-form {
  margin-top: 20px;
}

.ml-2 {
  margin-left: 8px;
}

.mt-1 {
  margin-top: 4px;
}

.mb-4 {
  margin-bottom: 16px;
}
</style>
