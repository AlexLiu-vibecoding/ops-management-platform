<template>
  <div class="environments-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>环境管理</span>
          <el-button type="primary" @click="handleAdd" v-if="isAdmin">
            <el-icon><Plus /></el-icon>
            添加环境
          </el-button>
        </div>
      </template>
      
      <el-table :data="environments" style="width: 100%">
        <el-table-column prop="name" label="环境名称" width="200" />
        <el-table-column prop="code" label="环境编码" width="150" />
        <el-table-column label="颜色标记" width="120">
          <template #default="{ row }">
            <span class="env-tag" :style="{ backgroundColor: row.color }">
              {{ row.name }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="require_approval" label="需要审批" width="100">
          <template #default="{ row }">
            <el-tag :type="row.require_approval ? 'warning' : 'success'" size="small">
              {{ row.require_approval ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status ? 'success' : 'info'" size="small">
              {{ row.status ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" show-overflow-tooltip />
        <el-table-column label="操作" width="150" v-if="isAdmin">
          <template #default="{ row }">
            <el-button text type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button text type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog v-model="dialog.visible" :title="dialog.isEdit ? '编辑环境' : '添加环境'" width="500px">
      <el-form :model="dialog.form" :rules="dialog.rules" ref="formRef" label-width="100px">
        <el-form-item label="环境名称" prop="name">
          <el-input v-model="dialog.form.name" placeholder="请输入环境名称" />
        </el-form-item>
        <el-form-item label="环境编码" prop="code">
          <el-input v-model="dialog.form.code" placeholder="请输入环境编码" />
        </el-form-item>
        <el-form-item label="颜色标记" prop="color">
          <el-color-picker v-model="dialog.form.color" />
        </el-form-item>
        <el-form-item label="需要审批" prop="require_approval">
          <el-switch v-model="dialog.form.require_approval" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="dialog.form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import request from '@/api/index'
import { useUserStore } from '@/stores/user'
import { ElMessage, ElMessageBox } from 'element-plus'

const userStore = useUserStore()
const isAdmin = computed(() => userStore.isAdmin)

const environments = ref([])
const formRef = ref(null)

const dialog = reactive({
  visible: false,
  isEdit: false,
  form: {
    name: '',
    code: '',
    color: '#52C41A',
    require_approval: true,
    description: ''
  },
  rules: {
    name: [{ required: true, message: '请输入环境名称', trigger: 'blur' }],
    code: [{ required: true, message: '请输入环境编码', trigger: 'blur' }]
  }
})

const fetchEnvironments = async () => {
  try {
    const data = await request.get('/environments')
    environments.value = data.items || data
  } catch (error) {
    console.error('获取环境列表失败:', error)
  }
}

const handleAdd = () => {
  dialog.isEdit = false
  dialog.form = { name: '', code: '', color: '#52C41A', require_approval: true, description: '' }
  dialog.visible = true
}

const handleEdit = (row) => {
  dialog.isEdit = true
  dialog.form = { ...row }
  dialog.visible = true
}

const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm('确定要删除该环境吗？', '警告', { type: 'warning' })
    await request.delete(`/environments/${row.id}`)
    ElMessage.success('删除成功')
    fetchEnvironments()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    try {
      if (dialog.isEdit) {
        await request.put(`/environments/${dialog.form.id}`, dialog.form)
        ElMessage.success('更新成功')
      } else {
        await request.post('/environments', dialog.form)
        ElMessage.success('添加成功')
      }
      dialog.visible = false
      fetchEnvironments()
    } catch (error) {
      console.error('操作失败:', error)
    }
  })
}

onMounted(() => {
  fetchEnvironments()
})
</script>

<style lang="scss" scoped>
.environments-page {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
