<template>
  <div class="aws-regions-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>AWS 区域管理</span>
          <el-button type="primary" @click="handleAdd" v-if="isAdmin">
            <el-icon><Plus /></el-icon>
            添加区域
          </el-button>
        </div>
      </template>
      
      <el-alert
        title="区域管理说明"
        type="info"
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #default>
          <p>此处管理 AWS 区域列表，用于环境配置和 RDS 实例管理。</p>
          <p style="margin-top: 4px;">禁用区域后，该区域将不会在下拉列表中显示，但已配置的实例不受影响。</p>
        </template>
      </el-alert>
      
      <el-table :data="regions" style="width: 100%" :show-overflow-tooltip="false" v-loading="loading">
        <el-table-column prop="region_code" label="区域代码" min-width="150">
          <template #default="{ row }">
            <code>{{ row.region_code }}</code>
          </template>
        </el-table-column>
        <el-table-column prop="region_name" label="区域名称" min-width="180" />
        <el-table-column prop="geo_group" label="地理分组" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.geo_group }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="display_order" label="排序" width="80" align="center" />
        <el-table-column prop="is_enabled" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch 
              :model-value="row.is_enabled" 
              @change="handleToggleEnabled(row, $event)"
              :disabled="!isAdmin"
            />
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="150">
          <template #default="{ row }">
            <span v-if="row.description">{{ row.description }}</span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" v-if="isAdmin" fixed="right" align="center">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" size="small" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="stats-bar">
        <el-tag type="info">总计: {{ regions.length }} 个区域</el-tag>
        <el-tag type="success" style="margin-left: 8px;">启用: {{ enabledCount }} 个</el-tag>
        <el-tag type="warning" style="margin-left: 8px;">禁用: {{ regions.length - enabledCount }} 个</el-tag>
      </div>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑区域' : '添加区域'" width="500px">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
        <el-form-item label="区域代码" prop="region_code">
          <el-input 
            v-model="dialog.form.region_code" 
            placeholder="如: ap-southeast-5"
            :disabled="dialog.isEdit"
          />
        </el-form-item>
        <el-form-item label="区域名称" prop="region_name">
          <el-input v-model="dialog.form.region_name" placeholder="如: 亚太地区(曼谷)" />
        </el-form-item>
        <el-form-item label="地理分组" prop="geo_group">
          <el-select v-model="dialog.form.geo_group" placeholder="选择分组" style="width: 100%;">
            <el-option label="美国" value="美国" />
            <el-option label="美洲其他" value="美洲其他" />
            <el-option label="欧洲" value="欧洲" />
            <el-option label="亚太" value="亚太" />
            <el-option label="中东" value="中东" />
            <el-option label="非洲" value="非洲" />
            <el-option label="中国" value="中国" />
          </el-select>
        </el-form-item>
        <el-form-item label="排序" prop="display_order">
          <el-input-number v-model="dialog.form.display_order" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="启用状态">
          <el-switch v-model="dialog.form.is_enabled" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="2" placeholder="可选描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const loading = ref(false)
const submitting = ref(false)
const regions = ref([])
const formRef = ref(null)

const enabledCount = computed(() => regions.value.filter(r => r.is_enabled).length)

const dialog = reactive({
  visible: false,
  isEdit: false,
  editingId: null,
  form: {
    region_code: '',
    region_name: '',
    geo_group: '亚太',
    display_order: 50,
    is_enabled: true,
    description: ''
  },
  rules: {
    region_code: [{ required: true, message: '请输入区域代码', trigger: 'blur' }],
    region_name: [{ required: true, message: '请输入区域名称', trigger: 'blur' }],
    geo_group: [{ required: true, message: '请选择地理分组', trigger: 'change' }]
  }
})

const fetchRegions = async () => {
  loading.value = true
  try {
    const data = await request.get('/aws-regions', { params: { enabled_only: false } })
    regions.value = data || []
  } catch (error) {
    console.error('获取区域列表失败:', error)
    ElMessage.error('获取区域列表失败')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  dialog.form = {
    region_code: '',
    region_name: '',
    geo_group: '亚太',
    display_order: 50,
    is_enabled: true,
    description: ''
  }
}

const handleAdd = () => {
  dialog.isEdit = false
  dialog.editingId = null
  resetForm()
  dialog.visible = true
}

const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.editingId = row.id
  dialog.form = {
    region_code: row.region_code,
    region_name: row.region_name,
    geo_group: row.geo_group,
    display_order: row.display_order,
    is_enabled: row.is_enabled,
    description: row.description || ''
  }
  dialog.visible = true
}

const handleToggleEnabled = async (row, value) => {
  try {
    await request.put(`/aws-regions/${row.id}`, { is_enabled: value })
    row.is_enabled = value
    ElMessage.success(value ? '已启用' : '已禁用')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(`确定要删除区域 "${row.region_name}" 吗？`, '警告', { type: 'warning' })
    await request.delete(`/aws-regions/${row.id}`)
    ElMessage.success('删除成功')
    fetchRegions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    submitting.value = true
    try {
      if (dialog.isEdit) {
        await request.put(`/aws-regions/${dialog.editingId}`, dialog.form)
        ElMessage.success('更新成功')
      } else {
        await request.post('/aws-regions', dialog.form)
        ElMessage.success('添加成功')
      }
      dialog.visible = false
      fetchRegions()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '操作失败')
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  fetchRegions()
})
</script>

<style lang="scss" scoped>
.aws-regions-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .stats-bar {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid #EBEEF5;
  }
  
  code {
    background: #f5f7fa;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }
}
</style>
