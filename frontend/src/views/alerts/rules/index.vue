<template>
  <div class="app-container">
    <!-- 搜索栏 -->
    <el-card shadow="never" class="mb-4">
      <el-form :inline="true" :model="queryParams" @submit.prevent="handleQuery">
        <el-form-item label="规则名称">
          <el-input v-model="queryParams.search" placeholder="请输入规则名称" clearable @keyup.enter="handleQuery" />
        </el-form-item>
        <el-form-item label="规则类型">
          <el-select v-model="queryParams.rule_type" placeholder="全部" clearable>
            <el-option v-for="item in ruleTypes" :key="item.value" :label="item.label" :value="item.value" />
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
          <span class="font-semibold">告警规则</span>
          <el-button type="primary" @click="handleAdd">
            <el-icon><Plus /></el-icon>
            新增规则
          </el-button>
        </div>
      </template>

      <!-- 数据表格 -->
      <el-table v-loading="loading" :data="tableData" stripe>
        <el-table-column prop="name" label="规则名称" min-width="150" />
        <el-table-column prop="rule_type_label" label="规则类型" width="120" />
        <el-table-column label="条件" min-width="150">
          <template #default="{ row }">
            {{ row.metric_name }} {{ row.operator_label }} {{ row.threshold }} (持续{{ row.duration }}s)
          </template>
        </el-table-column>
        <el-table-column label="告警级别" width="100">
          <template #default="{ row }">
            <el-tag :color="row.severity_color" class="text-white">
              {{ row.severity_label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="静默期" width="100">
          <template #default="{ row }">
            {{ row.silence_duration }}s
          </template>
        </el-table-column>
        <el-table-column prop="is_enabled" label="状态" min-width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'info'">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="触发次数" width="100">
          <template #default="{ row }">
            {{ row.trigger_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="操作" min-width="120" fixed="right" align="center">
          <template #default="{ row }">
            <TableActions :row="row" :actions="ruleActions" @edit="handleEdit" @toggle="handleToggle" @delete="handleDelete" />
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
        <el-form-item label="规则名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入规则名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="规则类型" prop="rule_type">
          <el-select v-model="form.rule_type" placeholder="请选择规则类型" class="w-full">
            <el-option v-for="item in ruleTypes" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
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
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="指标名称" prop="metric_name">
              <el-input v-model="form.metric_name" placeholder="如: cpu_usage" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="运算符" prop="operator">
              <el-select v-model="form.operator" placeholder="运算符">
                <el-option v-for="item in operators" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="阈值" prop="threshold">
              <el-input-number v-model="form.threshold" :precision="2" :min="0" class="w-full" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="持续时间" prop="duration">
              <el-input-number v-model="form.duration" :min="0" class="w-full" />
              <span class="ml-2 text-gray-500">秒</span>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="聚合方式" prop="aggregation">
              <el-select v-model="form.aggregation" placeholder="聚合方式" class="w-full">
                <el-option v-for="item in aggregations" :key="item.value" :label="item.label" :value="item.value" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="告警级别" prop="severity">
              <el-select v-model="form.severity" placeholder="告警级别" class="w-full">
                <el-option v-for="item in severities" :key="item.value" :label="item.label" :value="item.value">
                  <span :style="{ color: item.color }">{{ item.label }}</span>
                </el-option>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="静默时长" prop="silence_duration">
              <el-input-number v-model="form.silence_duration" :min="0" class="w-full" />
              <span class="ml-2 text-gray-500">秒</span>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="通知配置">
          <el-checkbox v-model="form.notify_enabled">启用通知</el-checkbox>
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus } from '@element-plus/icons-vue'
import { alertRulesApi } from '@/api/inspection'
import request from '@/api/index'
import TableActions from '@/components/TableActions.vue'

defineOptions({ name: 'AlertRules' })

// 操作列配置
const ruleActions = computed(() => [
  { key: 'edit', label: '编辑', event: 'edit', primary: true },
  { 
    key: 'toggle', 
    label: (row) => row.is_enabled ? '禁用' : '启用',
    event: 'toggle',
    primary: false
  },
  { key: 'delete', label: '删除', event: 'delete', danger: true, primary: false }
])

// 数据
const loading = ref(false)
const tableData = ref([])
const total = ref(0)
const instanceList = ref([])

// 下拉选项
const ruleTypes = ref([])
const operators = ref([])
const aggregations = ref([])
const severities = ref([])

// 查询参数
const queryParams = reactive({
  search: '',
  rule_type: '',
  is_enabled: undefined,
  page: 1,
  limit: 20
})

// 对话框
const dialogVisible = ref(false)
const dialogTitle = computed(() => (form.id ? '编辑规则' : '新增规则'))
const formRef = ref()
const submitLoading = ref(false)

// 表单
const form = reactive({
  id: 0,
  name: '',
  description: '',
  rule_type: '',
  instance_scope: 'all',
  instance_ids: [],
  metric_name: '',
  operator: '>',
  threshold: 0,
  duration: 60,
  aggregation: 'avg',
  severity: 'warning',
  silence_duration: 300,
  notify_enabled: true,
  is_enabled: true
})

// 表单校验
const rules = {
  name: [{ required: true, message: '请输入规则名称', trigger: 'blur' }],
  rule_type: [{ required: true, message: '请选择规则类型', trigger: 'change' }],
  metric_name: [{ required: true, message: '请输入指标名称', trigger: 'blur' }],
  threshold: [{ required: true, message: '请输入阈值', trigger: 'blur' }],
  severity: [{ required: true, message: '请选择告警级别', trigger: 'change' }]
}

// 初始化
onMounted(() => {
  loadData()
  loadOptions()
  loadInstances()
})

// 加载数据
async function loadData() {
  loading.value = true
  try {
    const data = await alertRulesApi.list(queryParams)
    tableData.value = data.items || []
    total.value = data.total || 0
  } catch (error) {
    console.error('加载数据失败:', error)
  } finally {
    loading.value = false
  }
}

// 加载下拉选项
async function loadOptions() {
  try {
    const [typesRes, opsRes, aggRes, sevRes] = await Promise.all([
      alertRulesApi.getTypes(),
      alertRulesApi.getOperators(),
      alertRulesApi.getAggregations(),
      alertRulesApi.getSeverities()
    ])
    ruleTypes.value = typesRes || []
    operators.value = opsRes || []
    aggregations.value = aggRes || []
    severities.value = sevRes || []
  } catch (error) {
    console.error('加载选项失败:', error)
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

// 查询
function handleQuery() {
  queryParams.page = 1
  loadData()
}

// 重置
function resetQuery() {
  queryParams.search = ''
  queryParams.rule_type = ''
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
    const data = await alertRulesApi.get(row.id)
    Object.assign(form, {
      id: data.id,
      name: data.name,
      description: data.description || '',
      rule_type: data.rule_type,
      instance_scope: data.instance_scope || 'all',
      instance_ids: data.instance_ids || [],
      metric_name: data.metric_name || '',
      operator: data.operator,
      threshold: data.threshold,
      duration: data.duration,
      aggregation: data.aggregation,
      severity: data.severity,
      silence_duration: data.silence_duration,
      notify_enabled: data.notify_enabled,
      is_enabled: data.is_enabled
    })
    dialogVisible.value = true
  } catch (error) {
    ElMessage.error('获取详情失败')
  }
}

// 删除
async function handleDelete(row) {
  await ElMessageBox.confirm('确定要删除该规则吗？', '警告', { type: 'warning' })
  try {
    await alertRulesApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

// 启用/禁用
async function handleToggle(row) {
  try {
    await alertRulesApi.toggle(row.id)
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
    if (form.id) {
      await alertRulesApi.update(form.id, form)
      ElMessage.success('更新成功')
    } else {
      await alertRulesApi.create(form)
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
  form.rule_type = ''
  form.instance_scope = 'all'
  form.instance_ids = []
  form.metric_name = ''
  form.operator = '>'
  form.threshold = 0
  form.duration = 60
  form.aggregation = 'avg'
  form.severity = 'warning'
  form.silence_duration = 300
  form.notify_enabled = true
  form.is_enabled = true
  formRef.value?.resetFields()
}
</script>
