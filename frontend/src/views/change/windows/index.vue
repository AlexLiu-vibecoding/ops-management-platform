<template>
  <div class="app-container">
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
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column label="时间范围" width="150">
          <template #default="{ row }">
            {{ row.start_time }} - {{ row.end_time }}
          </template>
        </el-table-column>
        <el-table-column prop="weekdays_label" label="星期" width="150" />
        <el-table-column label="允许紧急变更" width="110">
          <template #default="{ row }">
            <el-tag :type="row.allow_emergency ? 'success' : 'danger'" size="small">
              {{ row.allow_emergency ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="需要审批" width="90">
          <template #default="{ row }">
            <el-tag :type="row.require_approval ? 'warning' : 'success'" size="small">
              {{ row.require_approval ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最小审批人" width="100">
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
        <el-table-column label="操作" min-width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link :type="row.is_enabled ? 'warning' : 'success'" @click="handleToggle(row)">
              {{ row.is_enabled ? '禁用' : '启用' }}
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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
        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="允许紧急变更">
              <el-switch v-model="form.allow_emergency" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="需要审批">
              <el-switch v-model="form.require_approval" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最小审批人" prop="min_approvers">
              <el-input-number v-model="form.min_approvers" :min="1" :max="10" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="自动拒绝">
          <el-switch v-model="form.auto_reject_outside" />
          <span class="ml-2 text-gray-500">自动拒绝窗口外的变更申请</span>
        </el-form-item>
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
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { changeWindowsApi } from '@/api/inspection'
import request from '@/api/index'

defineOptions({ name: 'ChangeWindows' })

// 数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const environmentList = ref([])

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
    
    Object.assign(form, {
      id: data.id,
      name: data.name,
      description: data.description || '',
      environment_ids: data.environment_ids || [],
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
    ElMessage.error('操作失败')
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
