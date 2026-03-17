<template>
  <div class="monitor-settings">
    <el-card shadow="never" class="settings-card">
      <template #header>
        <span>监控配置</span>
      </template>
      
      <!-- 全局开关 -->
      <el-divider content-position="left">全局监控开关</el-divider>
      <el-row :gutter="20">
        <el-col :span="6" v-for="(enabled, type) in globalSwitches" :key="type">
          <div class="switch-item">
            <span class="switch-label">{{ getMonitorTypeLabel(type) }}</span>
            <el-switch
              v-model="globalSwitches[type]"
              :disabled="!isAdmin"
              @change="handleGlobalSwitchChange(type, $event)"
            />
          </div>
        </el-col>
      </el-row>
      
      <!-- 监控参数配置 -->
      <el-divider content-position="left">监控参数</el-divider>
      <el-form :model="monitorConfig" label-width="200px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="性能采集间隔(秒)">
              <el-input-number
                v-model="monitorConfig.monitor_collect_interval"
                :min="1"
                :max="60"
                :disabled="!isAdmin"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="慢查询阈值(秒)">
              <el-input-number
                v-model="monitorConfig.slow_query_threshold"
                :min="0.1"
                :max="60"
                :step="0.1"
                :precision="1"
                :disabled="!isAdmin"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="CPU告警阈值(%)">
              <el-input-number
                v-model="monitorConfig.cpu_threshold"
                :min="50"
                :max="100"
                :disabled="!isAdmin"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="性能数据保留天数">
              <el-input-number
                v-model="monitorConfig.performance_data_retention_days"
                :min="7"
                :max="90"
                :disabled="!isAdmin"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="快照保留天数">
              <el-input-number
                v-model="monitorConfig.snapshot_retention_days"
                :min="1"
                :max="30"
                :disabled="!isAdmin"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item v-if="isAdmin">
          <el-button type="primary" @click="saveConfig">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 告警规则配置 -->
    <el-card shadow="never" class="alert-rules-card">
      <template #header>
        <div class="card-header">
          <span>告警规则</span>
          <el-button type="primary" size="small" @click="addAlertRule" v-if="isAdmin">
            添加规则
          </el-button>
        </div>
      </template>
      
      <el-table :data="alertRules" style="width: 100%">
        <el-table-column prop="key" label="规则标识" width="300" />
        <el-table-column prop="value" label="阈值" width="150" />
        <el-table-column prop="description" label="描述" />
        <el-table-column label="操作" width="100" v-if="isAdmin">
          <template #default="{ row }">
            <el-button text type="primary" @click="editAlertRule(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 告警规则编辑对话框 -->
    <el-dialog v-model="ruleDialog.visible" title="编辑告警规则" width="500px">
      <el-form :model="ruleDialog.form" label-width="80px">
        <el-form-item label="规则标识">
          <el-input v-model="ruleDialog.form.key" :disabled="ruleDialog.isEdit" />
        </el-form-item>
        <el-form-item label="阈值">
          <el-input v-model="ruleDialog.form.value" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="ruleDialog.form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ruleDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveAlertRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { monitorApi } from '@/api/monitor'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const globalSwitches = reactive({
  slow_query: true,
  cpu_sql: true,
  performance: true,
  inspection: true
})

const monitorConfig = reactive({
  monitor_collect_interval: 10,
  slow_query_threshold: 1.0,
  cpu_threshold: 80,
  performance_data_retention_days: 30,
  snapshot_retention_days: 7
})

const alertRules = ref([])

const ruleDialog = reactive({
  visible: false,
  isEdit: false,
  form: {
    key: '',
    value: '',
    description: ''
  }
})

// 获取监控类型标签
const getMonitorTypeLabel = (type) => {
  const labels = {
    slow_query: '慢查询监控',
    cpu_sql: '高CPU SQL监控',
    performance: '性能监控',
    inspection: '实例巡检'
  }
  return labels[type] || type
}

// 获取全局开关
const fetchGlobalSwitches = async () => {
  try {
    const data = await monitorApi.getGlobalSwitches()
    Object.assign(globalSwitches, data)
  } catch (error) {
    console.error('获取全局开关失败:', error)
  }
}

// 处理全局开关变化
const handleGlobalSwitchChange = async (type, enabled) => {
  try {
    await monitorApi.updateGlobalSwitch({
      monitor_type: type,
      enabled: enabled
    })
    ElMessage.success(`${getMonitorTypeLabel(type)}已${enabled ? '启用' : '禁用'}`)
  } catch (error) {
    globalSwitches[type] = !enabled
  }
}

// 获取监控配置
const fetchMonitorConfig = async () => {
  try {
    const data = await monitorApi.getConfig()
    Object.assign(monitorConfig, data)
  } catch (error) {
    console.error('获取监控配置失败:', error)
  }
}

// 保存配置
const saveConfig = async () => {
  try {
    await monitorApi.updateConfig(monitorConfig)
    ElMessage.success('配置保存成功')
  } catch (error) {
    console.error('保存配置失败:', error)
  }
}

// 获取告警规则
const fetchAlertRules = async () => {
  try {
    alertRules.value = await monitorApi.getAlertRules()
  } catch (error) {
    console.error('获取告警规则失败:', error)
  }
}

// 添加告警规则
const addAlertRule = () => {
  ruleDialog.isEdit = false
  ruleDialog.form = { key: '', value: '', description: '' }
  ruleDialog.visible = true
}

// 编辑告警规则
const editAlertRule = (row) => {
  ruleDialog.isEdit = true
  ruleDialog.form = { ...row }
  ruleDialog.visible = true
}

// 保存告警规则
const saveAlertRule = async () => {
  try {
    const rules = [...alertRules.value]
    if (ruleDialog.isEdit) {
      const index = rules.findIndex(r => r.key === ruleDialog.form.key)
      if (index > -1) {
        rules[index] = { ...ruleDialog.form }
      }
    } else {
      rules.push({ ...ruleDialog.form })
    }
    
    await monitorApi.updateAlertRules(rules)
    ElMessage.success('保存成功')
    ruleDialog.visible = false
    fetchAlertRules()
  } catch (error) {
    console.error('保存告警规则失败:', error)
  }
}

onMounted(() => {
  fetchGlobalSwitches()
  fetchMonitorConfig()
  fetchAlertRules()
})
</script>

<style lang="scss" scoped>
.monitor-settings {
  .settings-card {
    margin-bottom: 20px;
    
    .switch-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      background: #f9f9f9;
      border-radius: 8px;
      margin-bottom: 10px;
      
      .switch-label {
        font-weight: 500;
      }
    }
  }
  
  .alert-rules-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
  }
}
</style>
