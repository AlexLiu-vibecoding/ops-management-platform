<template>
  <div class="app-container">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="任务名称">
          <el-input v-model="queryParams.search" placeholder="请输入任务名称" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="queryParams.status" placeholder="全部" clearable>
            <el-option label="启用" value="enabled" />
            <el-option label="禁用" value="disabled" />
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
          <span class="font-semibold">定时巡检任务</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增任务
          </el-button>
        </div>
      </template>

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="name" label="任务名称" min-width="150" />
        <el-table-column prop="description" label="描述" min-width="150" show-overflow-tooltip />
        <el-table-column prop="cron_expression" label="Cron表达式" width="130" />
        <el-table-column label="下次执行" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.next_run_time) }}
          </template>
        </el-table-column>
        <el-table-column label="最后执行" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.last_run_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'enabled' ? 'success' : 'info'">
              {{ row.status === 'enabled' ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="统计" width="120">
          <template #default="{ row }">
            <span class="text-success">{{ row.success_count }}</span> /
            <span class="text-danger">{{ row.fail_count }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleRun(row)">执行</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link :type="row.status === 'enabled' ? 'warning' : 'success'" @click="handleToggle(row)">
              {{ row.status === 'enabled' ? '禁用' : '启用' }}
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
        <el-form-item label="任务名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入任务名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="实例范围" prop="instance_scope">
          <el-radio-group v-model="form.instance_scope">
            <el-radio value="all">全部实例</el-radio>
            <el-radio value="selected">指定实例</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.instance_scope === 'selected'" label="选择实例">
          <el-select v-model="form.instance_ids" multiple placeholder="请选择实例" class="w-full">
            <el-option v-for="inst in instanceList" :key="inst.id" :label="inst.name" :value="inst.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="巡检模块">
          <el-checkbox-group v-model="form.modules">
            <el-checkbox v-for="mod in moduleList" :key="mod.value" :value="mod.value">{{ mod.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="Cron表达式" prop="cron_expression">
          <div class="flex gap-2 w-full">
            <el-input v-model="form.cron_expression" placeholder="0 0 2 * * ?" class="flex-1" @blur="validateCron" />
            <el-button @click="showCronHelper = true">助手</el-button>
          </div>
          <div v-if="cronNextTimes.length" class="mt-2 text-sm text-gray-500">
            <div>下次执行时间：</div>
            <div v-for="(time, idx) in cronNextTimes" :key="idx">{{ time }}</div>
          </div>
        </el-form-item>
        <el-form-item label="时区">
          <el-select v-model="form.timezone" placeholder="请选择时区" class="w-full">
            <el-option label="Asia/Shanghai (北京时间)" value="Asia/Shanghai" />
            <el-option label="UTC" value="UTC" />
          </el-select>
        </el-form-item>
        <el-form-item label="通知配置">
          <div class="flex flex-col gap-2">
            <el-checkbox v-model="form.notify_on_complete">完成时通知</el-checkbox>
            <el-checkbox v-model="form.notify_on_warning">发现警告时通知</el-checkbox>
            <el-checkbox v-model="form.notify_on_critical">发现严重问题时通知</el-checkbox>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitLoading" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- Cron表达式助手 -->
    <el-dialog v-model="showCronHelper" title="Cron表达式助手" width="500px">
      <div class="space-y-4">
        <div>
          <span class="font-medium">常用表达式：</span>
          <div class="mt-2 space-y-2">
            <div v-for="item in cronPresets" :key="item.value" 
                 class="flex justify-between items-center p-2 bg-gray-50 rounded cursor-pointer hover:bg-gray-100"
                 @click="selectCronPreset(item.value)">
              <span>{{ item.label }}</span>
              <span class="text-gray-500">{{ item.value }}</span>
            </div>
          </div>
        </div>
        <div class="text-sm text-gray-500">
          <p>格式：秒 分 时 日 月 周</p>
          <p>示例：0 0 2 * * ? 表示每天凌晨2点执行</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { scheduledInspectionApi } from '@/api/inspection'
import request from '@/api/index'

defineOptions({ name: 'ScheduledInspection' })

// 格式化日期时间
const formatDateTime = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

// 数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const instanceList = ref([])
const moduleList = ref([])

// 查询参数
const queryParams = reactive({
  search: '',
  status: '',
  page: 1,
  limit: 20
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (form.id ? '编辑任务' : '新增任务'))
const formRef = ref()
const submitLoading = ref(false)
const showCronHelper = ref(false)
const cronNextTimes = ref([])

// 表单
const form = reactive({
  id: 0,
  name: '',
  description: '',
  instance_scope: 'all',
  instance_ids: [],
  modules: [],
  cron_expression: '',
  timezone: 'Asia/Shanghai',
  notify_on_complete: true,
  notify_on_warning: true,
  notify_on_critical: true
})

// 表单校验
const rules = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  cron_expression: [{ required: true, message: '请输入Cron表达式', trigger: 'blur' }]
}

// Cron预设
const cronPresets = [
  { label: '每小时执行', value: '0 0 * * * ?' },
  { label: '每天凌晨2点', value: '0 0 2 * * ?' },
  { label: '每天上午9点', value: '0 0 9 * * ?' },
  { label: '每周一上午9点', value: '0 0 9 ? * MON' },
  { label: '每月1日凌晨2点', value: '0 0 2 1 * ?' }
]

// 初始化
onMounted(() => {
  loadData()
  loadInstances()
  loadModules()
})

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const data = await scheduledInspectionApi.list(queryParams)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载实例列表
async function loadInstances() {
  try {
    const data = await request.get('/rdb-instances', { params: { limit: 1000 } })
    instanceList.value = data.items || []
  } catch (error) {
    console.error('加载实例失败:', error)
  }
}

// 加载模块列表
async function loadModules() {
  try {
    const data = await scheduledInspectionApi.getModules()
    moduleList.value = data || []
  } catch (error) {
    console.error('加载模块失败:', error)
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
  queryParams.status = ''
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
    const data = await scheduledInspectionApi.get(row.id)
    Object.assign(form, {
      id: data.id,
      name: data.name,
      description: data.description || '',
      instance_scope: data.instance_scope || 'all',
      instance_ids: data.instance_ids || [],
      modules: data.modules || [],
      cron_expression: data.cron_expression,
      timezone: data.timezone || 'Asia/Shanghai',
      notify_on_complete: data.notify_on_complete,
      notify_on_warning: data.notify_on_warning,
      notify_on_critical: data.notify_on_critical
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 删除
async function handleDelete(row) {
  await ElMessageBox.confirm('确定要删除该任务吗？', '警告', { type: 'warning' })
  try {
    await scheduledInspectionApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 启用/禁用
async function handleToggle(row) {
  try {
    await scheduledInspectionApi.toggle(row.id)
    ElMessage.success('操作成功')
    loadData()
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 执行
async function handleRun(row) {
  try {
    const data = await scheduledInspectionApi.run(row.id)
    ElMessage.success(data.message || '任务已开始执行')
    loadData()
  } catch (error) {
    ElMessage.error('执行失败')
  }
}

// 验证Cron表达式
async function validateCron() {
  if (!form.cron_expression) return
  try {
    const data = await scheduledInspectionApi.validateCron(form.cron_expression)
    if (data.valid) {
      cronNextTimes.value = data.next_times || []
    } else {
      ElMessage.warning(data.error || 'Cron表达式格式错误')
      cronNextTimes.value = []
    }
  } catch (error) {
    cronNextTimes.value = []
  }
}

// 选择Cron预设
function selectCronPreset(value) {
  form.cron_expression = value
  validateCron()
  showCronHelper.value = false
}

// 提交
async function handleSubmit() {
  const valid = await formRef.value?.validate()
  if (!valid) return

  submitLoading.value = true
  try {
    if (form.id) {
      await scheduledInspectionApi.update(form.id, form)
      ElMessage.success('更新成功')
    } else {
      await scheduledInspectionApi.create(form)
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
  form.instance_scope = 'all'
  form.instance_ids = []
  form.modules = []
  form.cron_expression = ''
  form.timezone = 'Asia/Shanghai'
  form.notify_on_complete = true
  form.notify_on_warning = true
  form.notify_on_critical = true
  cronNextTimes.value = []
  formRef.value?.resetFields()
}
</script>
