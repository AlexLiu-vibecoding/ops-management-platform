<template>
  <div class="app-container">
    <!-- 当前状态卡片 -->
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-semibold">变更策略概览</span>
          <el-button text @click="checkCurrentWindow">
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>
      <div class="current-status">
        <el-row :gutter="20">
          <el-col :span="6">
            <div class="status-item">
              <span class="status-label">默认策略</span>
              <span class="status-value">
                <el-tag type="success">允许变更</el-tag>
              </span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="status-item">
              <span class="status-label">生效中的封禁窗口</span>
              <span class="status-value">{{ activeBanWindows }} 个</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="status-item">
              <span class="status-label">生效中的允许窗口</span>
              <span class="status-value">{{ activeAllowWindows }} 个</span>
            </div>
          </el-col>
          <el-col :span="6">
            <div class="status-item">
              <span class="status-label">允许紧急变更</span>
              <span class="status-value">
                <el-tag :type="allowEmergencyCount > 0 ? 'success' : 'info'">
                  {{ allowEmergencyCount }} 个窗口支持
                </el-tag>
              </span>
            </div>
          </el-col>
        </el-row>
        <el-divider />
        <div class="policy-tips">
          <el-icon><InfoFilled /></el-icon>
          <div class="tips-content">
            <p><strong>策略说明：</strong></p>
            <ul>
              <li><strong>封禁窗口</strong>：在指定时间段内<span class="text-danger">禁止变更</span>，适用于节假日、大促期间保障稳定性</li>
              <li><strong>允许窗口</strong>：只有在指定时间段内<span class="text-success">允许变更</span>，适用于严格管控的核心系统</li>
              <li>两者同时存在时，封禁窗口优先级更高</li>
            </ul>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 搜索栏 -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="窗口名称">
          <el-input v-model="queryParams.search" placeholder="请输入窗口名称" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="窗口类型">
          <el-select v-model="queryParams.window_type" placeholder="全部" clearable>
            <el-option label="封禁窗口" value="forbidden" />
            <el-option label="允许窗口" value="allowed" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.is_enabled" placeholder="全部" clearable>
            <el-option label="启用" :value="true" />
            <el-option label="禁用" :value="false" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleQuery">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetQuery">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 操作栏 -->
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-semibold">变更时间窗口</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增窗口
          </el-button>
        </div>
      </template>

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="name" label="窗口名称" min-width="150" />
        <el-table-column label="窗口类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.window_type === 'forbidden' ? 'danger' : 'success'" size="small">
              {{ row.window_type === 'forbidden' ? '封禁' : '允许' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
        <el-table-column label="日期范围" width="200">
          <template #default="{ row }">
            <span v-if="row.start_date && row.end_date">
              {{ row.start_date }} ~ {{ row.end_date }}
            </span>
            <span v-else class="text-gray-400">长期有效</span>
          </template>
        </el-table-column>
        <el-table-column label="每日时间" width="120">
          <template #default="{ row }">
            <span v-if="row.start_time && row.end_time">
              {{ row.start_time }} - {{ row.end_time }}
            </span>
            <span v-else class="text-gray-400">全天</span>
          </template>
        </el-table-column>
        <el-table-column prop="weekdays_label" label="星期" width="100" />
        <el-table-column label="紧急变更" width="80">
          <template #default="{ row }">
            <el-tag :type="row.allow_emergency ? 'success' : 'info'" size="small">
              {{ row.allow_emergency ? '允许' : '禁止' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions :row="row" :actions="windowActions" @edit="handleEdit" @toggle="handleToggle" @delete="handleDelete" />
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="mt-4 flex justify-end">
        <el-pagination
          v-model:current-page="queryParams.page"
          v-model:page-size="queryParams.limit"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleQuery"
          @current-change="handleQuery"
        />
      </div>
    </el-card>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px" @close="resetForm">
      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px">
        <el-form-item label="窗口名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入窗口名称，如：春节封禁期、双十一保障期" />
        </el-form-item>
        
        <el-form-item label="窗口类型" prop="window_type">
          <el-radio-group v-model="form.window_type">
            <el-radio value="forbidden">
              <span class="text-danger font-semibold">封禁窗口</span>
              <span class="text-gray-500 text-sm ml-2">- 在此时间段内禁止变更</span>
            </el-radio>
            <el-radio value="allowed">
              <span class="text-success font-semibold">允许窗口</span>
              <span class="text-gray-500 text-sm ml-2">- 只有在此时间段内才能变更</span>
            </el-radio>
          </el-radio-group>
          <div class="text-gray-500 text-sm mt-1">
            <template v-if="form.window_type === 'forbidden'">
              <el-icon><WarningFilled /></el-icon>
              适用于：节假日、大促期间、重要活动期间等需要保障稳定性的场景
            </template>
            <template v-else>
              <el-icon><InfoFilled /></el-icon>
              适用于：核心系统、严格管控环境，只允许特定时间窗口内变更
            </template>
          </div>
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述，如：春节期间暂停所有变更申请" />
        </el-form-item>
        
        <el-form-item label="应用环境">
          <el-select v-model="form.environment_ids" multiple placeholder="不选择则应用于所有环境" class="w-full">
            <el-option v-for="env in environmentList" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        
        <!-- 日期范围选择 -->
        <el-divider content-position="left">生效时间</el-divider>
        <el-form-item label="日期范围">
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="w-full"
          />
          <div class="text-gray-500 text-sm mt-1">
            <template v-if="form.window_type === 'forbidden'">
              例：春节期间 2026-02-08 至 2026-02-15 禁止变更
            </template>
            <template v-else>
              例：维护窗口 2026-03-01 至 2026-03-31 仅此期间可变更
            </template>
          </div>
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="每日开始">
              <el-time-picker
                v-model="form.start_time_obj"
                format="HH:mm"
                placeholder="开始时间"
                class="w-full"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="每日结束">
              <el-time-picker
                v-model="form.end_time_obj"
                format="HH:mm"
                placeholder="结束时间"
                class="w-full"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <div class="text-gray-500 text-sm ml-[120px] -mt-2 mb-4">
          不选择则全天生效
        </div>
        
        <el-form-item label="允许星期">
          <el-checkbox-group v-model="form.weekdays">
            <el-checkbox v-for="(name, idx) in weekdayNames" :key="idx" :value="idx">
              {{ name }}
            </el-checkbox>
          </el-checkbox-group>
          <div class="text-gray-500 text-sm mt-1">不选择则每天都生效</div>
        </el-form-item>
        
        <!-- 审批配置 -->
        <el-divider content-position="left">其他配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="允许紧急变更">
              <el-switch v-model="form.allow_emergency" />
              <span class="ml-2 text-gray-500 text-sm">窗口外/封禁期间可提交紧急变更</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最小审批人">
              <el-input-number v-model="form.min_approvers" :min="1" :max="10" />
              <span class="ml-2 text-gray-500 text-sm">人</span>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, InfoFilled, WarningFilled } from '@element-plus/icons-vue'
import { changeWindowsApi } from '@/api/inspection'
import request from '@/api/index'
import TableActions from '@/components/TableActions.vue'

// 操作列配置
const windowActions = computed(() => [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { 
    key: 'toggle', 
    label: (row) => row.is_enabled ? '禁用' : '启用',
    event: 'toggle',
    primary: false
  },
  { key: 'delete', label: '删除', event: 'delete', danger: true, primary: false }
])

defineOptions({ name: 'ChangeWindows' })

// 数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const environmentList = ref([])

// 计算属性
const activeBanWindows = computed(() => {
  const now = new Date()
  return tableData.value.filter(w => {
    if (!w.is_enabled || w.window_type !== 'forbidden') return false
    if (w.start_date && w.end_date) {
      const start = new Date(w.start_date)
      const end = new Date(w.end_date)
      return now >= start && now <= end
    }
    return true
  }).length
})

const activeAllowWindows = computed(() => {
  const now = new Date()
  return tableData.value.filter(w => {
    if (!w.is_enabled || w.window_type !== 'allowed') return false
    if (w.start_date && w.end_date) {
      const start = new Date(w.start_date)
      const end = new Date(w.end_date)
      return now >= start && now <= end
    }
    return true
  }).length
})

const allowEmergencyCount = computed(() => {
  return tableData.value.filter(w => w.is_enabled && w.allow_emergency).length
})

// 检查当前窗口状态
const checkCurrentWindow = () => {
  loadData()
}

// 星期名称
const weekdayNames = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 查询参数
const queryParams = reactive({
  search: '',
  window_type: undefined,
  is_enabled: undefined,
  page: 1,
  limit: 20
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (form.id ? '编辑窗口' : '新增窗口'))
const formRef = ref()
const submitLoading = ref(false)

// 表单
const form = reactive({
  id: 0,
  name: '',
  window_type: 'forbidden',  // 默认封禁窗口
  description: '',
  environment_ids: [],
  dateRange: null,
  start_time: '',
  start_time_obj: null,
  end_time: '',
  end_time_obj: null,
  weekdays: [],
  allow_emergency: false,
  min_approvers: 1
})

// 表单校验
const rules = {
  name: [{ required: true, message: '请输入窗口名称', trigger: 'blur' }],
  window_type: [{ required: true, message: '请选择窗口类型', trigger: 'change' }]
}

// 监听时间选择器变化
watch(() => form.start_time_obj, (val) => {
  if (val) {
    form.start_time = `${String(val.getHours()).padStart(2, '0')}:${String(val.getMinutes()).padStart(2, '0')}`
  }
})

watch(() => form.end_time_obj, (val) => {
  if (val) {
    form.end_time = `${String(val.getHours()).padStart(2, '0')}:${String(val.getMinutes()).padStart(2, '0')}`
  }
})

// 初始化
onMounted(() => {
  loadData()
  loadEnvironments()
})

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const data = await changeWindowsApi.list(queryParams)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载环境列表
async function loadEnvironments() {
  try {
    const data = await request.get('/environments', { params: { limit: 100 } })
    environmentList.value = data.items || []
  } catch (error) {
    console.error('加载环境失败:', error)
  }
}

// 查询
function handleQuery() {
  queryParams.page = 1
  loadData()
}

// 重置
function resetQuery() {
  queryParams.search = ''
  queryParams.window_type = undefined
  queryParams.is_enabled = undefined
  handleQuery()
}

// 新增
function handleAdd() {
  resetForm()
  dialogVisible.value = true
}

// 编辑
async function handleEdit(row) {
  resetForm()
  try {
    const data = await changeWindowsApi.get(row.id)
    
    // 解析时间字符串为时间对象
    let start_time_obj = null
    let end_time_obj = null
    
    if (data.start_time) {
      const [startHour, startMin] = data.start_time.split(':').map(Number)
      start_time_obj = new Date()
      start_time_obj.setHours(startHour, startMin, 0, 0)
    }
    
    if (data.end_time) {
      const [endHour, endMin] = data.end_time.split(':').map(Number)
      end_time_obj = new Date()
      end_time_obj.setHours(endHour, endMin, 0, 0)
    }
    
    // 处理日期范围
    let dateRange = null
    if (data.start_date && data.end_date) {
      dateRange = [data.start_date, data.end_date]
    }
    
    Object.assign(form, {
      id: data.id,
      name: data.name,
      window_type: data.window_type || 'forbidden',
      description: data.description || '',
      environment_ids: data.environment_ids || [],
      dateRange: dateRange,
      start_time: data.start_time || '',
      start_time_obj: start_time_obj,
      end_time: data.end_time || '',
      end_time_obj: end_time_obj,
      weekdays: data.weekdays || [],
      allow_emergency: data.allow_emergency,
      min_approvers: data.min_approvers || 1
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 删除
async function handleDelete(row) {
  const typeName = row.window_type === 'forbidden' ? '封禁窗口' : '允许窗口'
  await ElMessageBox.confirm(`确定要删除${typeName}"${row.name}"吗？`, '警告', { type: 'warning' })
  try {
    await changeWindowsApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 启用/禁用
async function handleToggle(row) {
  try {
    await changeWindowsApi.toggle(row.id)
    ElMessage.success('操作成功')
    loadData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 提交
async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitLoading.value = true
  try {
    const submitData = {
      name: form.name,
      window_type: form.window_type,
      description: form.description,
      environment_ids: form.environment_ids,
      start_time: form.start_time || null,
      end_time: form.end_time || null,
      weekdays: form.weekdays.length > 0 ? form.weekdays : null,
      allow_emergency: form.allow_emergency,
      min_approvers: form.min_approvers
    }
    
    // 添加日期范围
    if (form.dateRange && form.dateRange.length === 2) {
      submitData.start_date = form.dateRange[0]
      submitData.end_date = form.dateRange[1]
    }

    if (form.id) {
      await changeWindowsApi.update(form.id, submitData)
      ElMessage.success('更新成功')
    } else {
      await changeWindowsApi.create(submitData)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    submitLoading.value = false
  }
}

// 重置表单
function resetForm() {
  form.id = 0
  form.name = ''
  form.window_type = 'forbidden'
  form.description = ''
  form.environment_ids = []
  form.dateRange = null
  form.start_time = ''
  form.start_time_obj = null
  form.end_time = ''
  form.end_time_obj = null
  form.weekdays = []
  form.allow_emergency = false
  form.min_approvers = 1
  formRef.value?.resetFields()
}
</script>

<style lang="scss" scoped>
.current-status {
  .status-item {
    display: flex;
    flex-direction: column;
    gap: 8px;
    
    .status-label {
      font-size: 13px;
      color: #909399;
    }
    
    .status-value {
      font-size: 18px;
      font-weight: 500;
      color: #303133;
    }
  }
  
  .policy-tips {
    display: flex;
    gap: 12px;
    padding: 16px;
    background: #f4f4f5;
    border-radius: 4px;
    font-size: 13px;
    color: #606266;
    
    .el-icon {
      color: #909399;
      margin-top: 2px;
    }
    
    .tips-content {
      flex: 1;
      
      p {
        margin: 0 0 8px 0;
      }
      
      ul {
        margin: 0;
        padding-left: 20px;
        
        li {
          margin: 4px 0;
        }
      }
    }
  }
}

.text-gray-400 {
  color: #9ca3af;
}

.text-danger {
  color: var(--el-color-danger);
}

.text-success {
  color: var(--el-color-success);
}

.font-semibold {
  font-weight: 600;
}
</style>
