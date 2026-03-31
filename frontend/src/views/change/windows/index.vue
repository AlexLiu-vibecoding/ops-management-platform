<template>
  <div class="app-container">
    <!-- 当前状态卡片 -->
    <el-card shadow="never" class="mb-4">
      <template #header>
        <div class="flex justify-between items-center">
          <span class="font-semibold">当前变更状态</span>
          <el-button text @click="checkCurrentWindow">
            <el-icon><Refresh /></el-icon>
            刷新状态
          </el-button>
        </div>
      </template>
      <div class="current-status">
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="status-item">
              <span class="status-label">全局默认策略</span>
              <span class="status-value">
                <el-tag v-if="!hasEnabledWindows" type="success">无限制</el-tag>
                <el-tag v-else type="warning">已配置变更窗口</el-tag>
              </span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="status-item">
              <span class="status-label">已启用窗口数</span>
              <span class="status-value">{{ enabledWindowsCount }} 个</span>
            </div>
          </el-col>
          <el-col :span="8">
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
          <span v-if="!hasEnabledWindows">
            未配置变更窗口时，所有变更申请将不受时间限制，直接进入审批流程。
          </span>
          <span v-else>
            已配置变更窗口后，只有在窗口内的变更才能提交。如需在窗口外变更，请确保窗口开启"允许紧急变更"选项。
          </span>
        </div>
      </div>
    </el-card>

    <!-- 搜索栏 -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="窗口名称">
          <el-input v-model="queryParams.search" placeholder="请输入窗口名称" clearable @keyup.enter="handleQuery" />
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
        <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
        <el-table-column label="日期范围" width="200">
          <template #default="{ row }">
            <span v-if="row.start_date && row.end_date">
              {{ row.start_date }} ~ {{ row.end_date }}
            </span>
            <span v-else class="text-gray-400">长期有效</span>
          </template>
        </el-table-column>
        <el-table-column label="时间范围" width="120">
          <template #default="{ row }">
            {{ row.start_time }} - {{ row.end_time }}
          </template>
        </el-table-column>
        <el-table-column prop="weekdays_label" label="星期" width="100" />
        <el-table-column label="允许紧急变更" width="100">
          <template #default="{ row }">
            <el-tag :type="row.allow_emergency ? 'success' : 'danger'" size="small">
              {{ row.allow_emergency ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最小审批人" width="90">
          <template #default="{ row }">
            {{ row.min_approvers }} 人
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="120" fixed="right" align="center">
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
          <el-input v-model="form.name" placeholder="请输入窗口名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="应用环境">
          <el-select v-model="form.environment_ids" multiple placeholder="不选择则应用于所有环境" class="w-full">
            <el-option v-for="env in environmentList" :key="env.id" :label="env.name" :value="env.id" />
          </el-select>
        </el-form-item>
        
        <!-- 日期范围选择 -->
        <el-divider content-position="left">日期范围（可选）</el-divider>
        <el-form-item label="生效日期">
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            class="w-full"
          />
          <div class="text-gray-500 text-sm mt-1">不选择则长期有效</div>
        </el-form-item>
        
        <!-- 时间范围选择 -->
        <el-divider content-position="left">每日时间范围</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="开始时间" prop="start_time">
              <el-time-picker
                v-model="form.start_time_obj"
                format="HH:mm"
                placeholder="开始时间"
                class="w-full"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="结束时间" prop="end_time">
              <el-time-picker
                v-model="form.end_time_obj"
                format="HH:mm"
                placeholder="结束时间"
                class="w-full"
              />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="允许星期">
          <el-checkbox-group v-model="form.weekdays">
            <el-checkbox v-for="(name, idx) in weekdayNames" :key="idx" :value="idx">
              {{ name }}
            </el-checkbox>
          </el-checkbox-group>
          <div class="text-gray-500 text-sm mt-1">不选择则每天都可以</div>
        </el-form-item>
        
        <!-- 审批配置 -->
        <el-divider content-position="left">审批配置</el-divider>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="需要审批">
              <el-switch v-model="form.require_approval" />
              <span class="ml-2 text-gray-500 text-sm">窗口内的变更是否需要审批</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="最小审批人" prop="min_approvers">
              <el-input-number v-model="form.min_approvers" :min="1" :max="10" />
              <span class="ml-2 text-gray-500 text-sm">人</span>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="允许紧急变更">
              <el-switch v-model="form.allow_emergency" />
              <span class="ml-2 text-gray-500 text-sm">窗口外可提交紧急变更</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="自动拒绝">
              <el-switch v-model="form.auto_reject_outside" />
              <span class="ml-2 text-gray-500 text-sm">自动拒绝窗口外的变更申请</span>
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
import { Search, Refresh, Plus, InfoFilled } from '@element-plus/icons-vue'
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
const hasEnabledWindows = computed(() => {
  return tableData.value.some(w => w.is_enabled)
})

const enabledWindowsCount = computed(() => {
  return tableData.value.filter(w => w.is_enabled).length
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
  description: '',
  environment_ids: [],
  dateRange: null,  // 日期范围 [start_date, end_date]
  start_time: '',
  start_time_obj: null,
  end_time: '',
  end_time_obj: null,
  weekdays: [],
  allow_emergency: false,
  require_approval: true,
  min_approvers: 1,
  auto_reject_outside: false
})

// 表单校验
const rules = {
  name: [{ required: true, message: '请输入窗口名称', trigger: 'blur' }],
  start_time: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  end_time: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  min_approvers: [{ required: true, message: '请输入最小审批人数', trigger: 'blur' }]
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
    const [startHour, startMin] = data.start_time.split(':').map(Number)
    const [endHour, endMin] = data.end_time.split(':').map(Number)
    
    const startDate = new Date()
    startDate.setHours(startHour, startMin, 0, 0)
    
    const endDate = new Date()
    endDate.setHours(endHour, endMin, 0, 0)
    
    // 处理日期范围
    let dateRange = null
    if (data.start_date && data.end_date) {
      dateRange = [data.start_date, data.end_date]
    }
    
    Object.assign(form, {
      id: data.id,
      name: data.name,
      description: data.description || '',
      environment_ids: data.environment_ids || [],
      dateRange: dateRange,
      start_time: data.start_time,
      start_time_obj: startDate,
      end_time: data.end_time,
      end_time_obj: endDate,
      weekdays: data.weekdays || [],
      allow_emergency: data.allow_emergency,
      require_approval: data.require_approval,
      min_approvers: data.min_approvers,
      auto_reject_outside: data.auto_reject_outside
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 删除
async function handleDelete(row) {
  await ElMessageBox.confirm('确定要删除该时间窗口吗？', '警告', { type: 'warning' })
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

  if (!form.start_time || !form.end_time) {
    ElMessage.warning('请选择开始和结束时间')
    return
  }

  submitLoading.value = true
  try {
    const submitData = {
      name: form.name,
      description: form.description,
      environment_ids: form.environment_ids,
      start_time: form.start_time,
      end_time: form.end_time,
      weekdays: form.weekdays.length > 0 ? form.weekdays : null,
      allow_emergency: form.allow_emergency,
      require_approval: form.require_approval,
      min_approvers: form.min_approvers,
      auto_reject_outside: form.auto_reject_outside
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
  form.description = ''
  form.environment_ids = []
  form.dateRange = null
  form.start_time = ''
  form.start_time_obj = null
  form.end_time = ''
  form.end_time_obj = null
  form.weekdays = []
  form.allow_emergency = false
  form.require_approval = true
  form.min_approvers = 1
  form.auto_reject_outside = false
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
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background: #f4f4f5;
    border-radius: 4px;
    font-size: 13px;
    color: #606266;
    
    .el-icon {
      color: #909399;
    }
  }
}

.text-gray-400 {
  color: #9ca3af;
}
</style>
