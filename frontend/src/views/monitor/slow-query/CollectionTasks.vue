<template>
  <div class="collection-tasks">
    <!-- 工具栏 -->
    <el-card shadow="never" class="toolbar-card">
      <div class="toolbar">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建任务
        </el-button>
        <el-button @click="fetchData" :loading="loading">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </el-card>
    
    <!-- 任务列表 -->
    <el-card shadow="never" class="table-card">
      <el-table :data="tasks" v-loading="loading" style="width: 100%">
        <el-table-column label="实例" min-width="150">
          <template #default="{ row }">
            <div class="instance-cell">
              <span class="instance-name">{{ row.instance_name || getInstanceName(row.instance_id) }}</span>
              <el-tag size="small" :type="row.enabled ? 'success' : 'info'">
                {{ row.enabled ? '启用' : '禁用' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="采集周期" width="120">
          <template #default="{ row }">
            <code class="cron-code">{{ row.cron_expression }}</code>
          </template>
        </el-table-column>
        
        <el-table-column label="耗时阈值" width="100" align="center">
          <template #default="{ row }">
            {{ row.min_exec_time }}s
          </template>
        </el-table-column>
        
        <el-table-column label="采集数量" width="100" align="center">
          <template #default="{ row }">
            Top {{ row.top_n }}
          </template>
        </el-table-column>
        
        <el-table-column label="自动分析" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.auto_analyze" class="success-icon"><CircleCheck /></el-icon>
            <el-icon v-else class="disabled-icon"><CircleClose /></el-icon>
          </template>
        </el-table-column>
        
        <el-table-column label="LLM 分析" width="100" align="center">
          <template #default="{ row }">
            <el-icon v-if="row.llm_analysis" class="success-icon"><CircleCheck /></el-icon>
            <el-icon v-else class="disabled-icon"><CircleClose /></el-icon>
          </template>
        </el-table-column>
        
        <el-table-column label="上次运行" width="160">
          <template #default="{ row }">
            <div class="last-run">
              <div class="run-time">{{ formatTime(row.last_run_at) }}</div>
              <el-tag 
                v-if="row.last_run_status" 
                :type="row.last_run_status === 'success' ? 'success' : (row.last_run_status === 'failed' ? 'danger' : 'warning')"
                size="small"
              >
                {{ row.last_run_status === 'success' ? '成功' : (row.last_run_status === 'failed' ? '失败' : '部分成功') }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="采集统计" width="120">
          <template #default="{ row }">
            <div class="stats-cell">
              <div>本次: {{ row.last_collected_count }}</div>
              <div class="total">累计: {{ row.total_collected_count }}</div>
            </div>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="runTask(row)" :loading="row.running">
              运行
            </el-button>
            <el-button size="small" @click="showEditDialog(row)">编辑</el-button>
            <el-button type="danger" size="small" @click="deleteTask(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @size-change="fetchData"
          @current-change="fetchData"
        />
      </div>
    </el-card>
    
    <!-- 创建/编辑对话框 -->
    <el-dialog 
      v-model="dialog.visible" 
      :title="dialog.isEdit ? '编辑采集任务' : '新建采集任务'" 
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="120px">
        <el-form-item label="实例" prop="instance_id">
          <el-select 
            v-model="dialog.form.instance_id" 
            placeholder="选择实例" 
            style="width: 100%;"
            :disabled="dialog.isEdit"
          >
            <el-option
              v-for="inst in availableInstances"
              :key="inst.id"
              :label="inst.name"
              :value="inst.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="启用状态">
          <el-switch v-model="dialog.form.enabled" />
        </el-form-item>
        
        <el-form-item label="采集周期" prop="cron_expression">
          <el-input v-model="dialog.form.cron_expression" placeholder="Cron 表达式">
            <template #append>
              <el-tooltip content="默认每5分钟执行一次">
                <el-icon><QuestionFilled /></el-icon>
              </el-tooltip>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item label="最小执行时间" prop="min_exec_time">
          <el-input-number 
            v-model="dialog.form.min_exec_time" 
            :min="0.1" 
            :max="3600" 
            :step="0.5" 
            :precision="1"
            style="width: 200px;"
          />
          <span class="unit-label">秒（只采集执行时间超过此阈值的慢SQL）</span>
        </el-form-item>
        
        <el-form-item label="采集数量" prop="top_n">
          <el-input-number 
            v-model="dialog.form.top_n" 
            :min="10" 
            :max="1000" 
            :step="10"
            style="width: 200px;"
          />
          <span class="unit-label">条（每次采集 Top N 最慢的SQL）</span>
        </el-form-item>
        
        <el-divider content-position="left">分析配置</el-divider>
        
        <el-form-item label="自动分析">
          <el-switch v-model="dialog.form.auto_analyze" />
          <span class="hint">采集后自动生成优化建议</span>
        </el-form-item>
        
        <el-form-item label="分析阈值" v-if="dialog.form.auto_analyze">
          <el-input-number 
            v-model="dialog.form.analyze_threshold" 
            :min="1" 
            :max="100"
            style="width: 200px;"
          />
          <span class="unit-label">次（执行次数超过此阈值才分析）</span>
        </el-form-item>
        
        <el-form-item label="LLM 分析" v-if="dialog.form.auto_analyze">
          <el-switch v-model="dialog.form.llm_analysis" />
          <span class="hint">使用大模型进行深度分析</span>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="submitForm" :loading="dialog.submitting">
          {{ dialog.isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, CircleCheck, CircleClose, QuestionFilled } from '@element-plus/icons-vue'
import request from '@/api/index'
import dayjs from 'dayjs'

const loading = ref(false)
const tasks = ref([])
const instances = ref([])
const formRef = ref(null)

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

const dialog = reactive({
  visible: false,
  isEdit: false,
  submitting: false,
  taskId: null,
  form: {
    instance_id: null,
    enabled: true,
    cron_expression: '0 */5 * * *',
    min_exec_time: 1.0,
    top_n: 100,
    auto_analyze: true,
    analyze_threshold: 3,
    llm_analysis: true
  },
  rules: {
    instance_id: [{ required: true, message: '请选择实例', trigger: 'change' }],
    cron_expression: [{ required: true, message: '请输入采集周期', trigger: 'blur' }],
    min_exec_time: [{ required: true, message: '请输入最小执行时间', trigger: 'blur' }],
    top_n: [{ required: true, message: '请输入采集数量', trigger: 'blur' }]
  }
})

// 可用的实例（排除已有任务的实例，编辑时除外）
const availableInstances = computed(() => {
  const usedInstanceIds = tasks.value
    .filter(t => !dialog.isEdit || t.id !== dialog.taskId)
    .map(t => t.instance_id)
  return instances.value.filter(inst => !usedInstanceIds.includes(inst.id))
})

// 获取实例列表
const fetchInstances = async () => {
  try {
    const data = await request.get('/instances', { params: { limit: 100 } })
    instances.value = (data.items || []).filter(inst => inst.db_type !== 'redis')
  } catch (error) {
    console.error('获取实例列表失败:', error)
    // 不显示错误消息，因为这个错误不是致命的
  }
}

// 获取任务列表
const fetchData = async () => {
  loading.value = true
  try {
    const data = await request.get('/sql-optimization/tasks', {
      params: {
        page: pagination.page,
        page_size: pagination.page_size
      }
    })
    tasks.value = data.items || []
    pagination.total = data.total || 0
  } catch (error) {
    console.error('获取采集任务失败:', error)
    // 如果是404错误，说明没有数据，设置空列表
    if (error.response?.status === 404) {
      tasks.value = []
      pagination.total = 0
    } else {
      ElMessage.error(error.response?.data?.message || '获取采集任务失败，请刷新页面重试')
    }
  } finally {
    loading.value = false
  }
}

// 显示创建对话框
const showCreateDialog = () => {
  dialog.isEdit = false
  dialog.taskId = null
  dialog.form = {
    instance_id: null,
    enabled: true,
    cron_expression: '0 */5 * * *',
    min_exec_time: 1.0,
    top_n: 100,
    auto_analyze: true,
    analyze_threshold: 3,
    llm_analysis: true
  }
  dialog.visible = true
}

// 显示编辑对话框
const showEditDialog = (row) => {
  dialog.isEdit = true
  dialog.taskId = row.id
  dialog.form = {
    instance_id: row.instance_id,
    enabled: row.enabled,
    cron_expression: row.cron_expression,
    min_exec_time: row.min_exec_time,
    top_n: row.top_n,
    auto_analyze: row.auto_analyze,
    analyze_threshold: row.analyze_threshold,
    llm_analysis: row.llm_analysis
  }
  dialog.visible = true
}

// 提交表单
const submitForm = async () => {
  if (!formRef.value) return
  
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  
  dialog.submitting = true
  try {
    if (dialog.isEdit) {
      await request.put(`/sql-optimization/tasks/${dialog.taskId}`, dialog.form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/sql-optimization/tasks', dialog.form)
      ElMessage.success('创建成功')
    }
    dialog.visible = false
    fetchData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    dialog.submitting = false
  }
}

// 运行任务
const runTask = async (row) => {
  row.running = true
  try {
    const data = await request.post(`/sql-optimization/tasks/${row.id}/run`)
    ElMessage.success(`采集完成，共 ${data.collected_count} 条，分析 ${data.analyzed_count} 条`)
    fetchData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '运行失败')
  } finally {
    row.running = false
  }
}

// 删除任务
const deleteTask = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该采集任务吗？',
      '确认删除',
      { type: 'warning' }
    )
    
    await request.delete(`/sql-optimization/tasks/${row.id}`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 获取实例名称
const getInstanceName = (instanceId) => {
  const inst = instances.value.find(i => i.id === instanceId)
  return inst?.name || '-'
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('MM-DD HH:mm') : '-'
}

// 暴露方法供父组件调用
defineExpose({
  fetchData
})

onMounted(() => {
  fetchInstances()
  fetchData()
})
</script>

<style lang="scss" scoped>
.collection-tasks {
  .toolbar-card {
    margin-bottom: 20px;
    
    .toolbar {
      display: flex;
      gap: 10px;
    }
  }
  
  .table-card {
    .instance-cell {
      display: flex;
      align-items: center;
      gap: 8px;
      
      .instance-name {
        font-weight: 500;
      }
    }
    
    .cron-code {
      font-family: monospace;
      background: #f5f7fa;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 12px;
    }
    
    .success-icon {
      color: #67c23a;
    }
    
    .disabled-icon {
      color: #c0c4cc;
    }
    
    .last-run {
      .run-time {
        font-size: 12px;
        color: #909399;
        margin-bottom: 4px;
      }
    }
    
    .stats-cell {
      font-size: 12px;
      
      .total {
        color: #909399;
      }
    }
  }
  
  .pagination {
    margin-top: 15px;
    display: flex;
    justify-content: flex-end;
  }
  
  .unit-label {
    margin-left: 10px;
    color: #909399;
    font-size: 12px;
  }
  
  .hint {
    margin-left: 10px;
    color: #909399;
    font-size: 12px;
  }
}
</style>
