<template>
  <div class="file-upload">
    <!-- 上传区域 -->
    <el-card class="upload-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>上传慢日志文件</span>
          <el-tag type="info" size="small">文件保留30天</el-tag>
        </div>
      </template>
      
      <el-form :model="uploadForm" label-width="100px" :rules="rules" ref="formRef">
        <el-form-item label="选择实例" prop="instanceId">
          <el-select
            v-model="uploadForm.instanceId"
            placeholder="请选择数据库实例"
            style="width: 100%"
            filterable
          >
            <el-option
              v-for="instance in instances"
              :key="instance.id"
              :label="instance.name"
              :value="instance.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="文件上传" prop="file">
          <el-upload
            ref="uploadRef"
            class="upload-dragger"
            drag
            :auto-upload="false"
            :limit="1"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :file-list="fileList"
            accept=".log,.txt"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 MySQL/PostgreSQL 慢查询日志文件，格式为 .log 或 .txt，单个文件不超过 50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item label="自动分析">
          <el-switch v-model="uploadForm.autoAnalyze" />
          <span class="form-tip">开启后将自动解析并分析上传的文件</span>
        </el-form-item>
        
        <el-form-item>
          <el-button
            type="primary"
            @click="handleUpload"
            :loading="uploading"
            :disabled="!uploadForm.instanceId || fileList.length === 0"
          >
            <el-icon v-if="!uploading"><upload /></el-icon>
            {{ uploading ? '上传中...' : '开始上传' }}
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 上传文件列表 -->
    <el-card class="file-list-card" shadow="hover" style="margin-top: 20px">
      <template #header>
        <div class="card-header">
          <span>上传历史</span>
          <el-button
            type="primary"
            size="small"
            @click="fetchFiles"
            :loading="loading"
          >
            刷新
          </el-button>
        </div>
      </template>
      
      <!-- 筛选 -->
      <div class="filter-bar">
        <el-select
          v-model="filters.instanceId"
          placeholder="选择实例"
          clearable
          style="width: 200px"
          @change="handleFilter"
        >
          <el-option
            v-for="instance in instances"
            :key="instance.id"
            :label="instance.name"
            :value="instance.id"
          />
        </el-select>
        
        <el-select
          v-model="filters.parseStatus"
          placeholder="解析状态"
          clearable
          style="width: 120px; margin-left: 10px"
          @change="handleFilter"
        >
          <el-option label="待解析" value="pending" />
          <el-option label="解析中" value="parsing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        
        <el-select
          v-model="filters.analyzeStatus"
          placeholder="分析状态"
          clearable
          style="width: 120px; margin-left: 10px"
          @change="handleFilter"
        >
          <el-option label="待分析" value="pending" />
          <el-option label="分析中" value="analyzing" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
      </div>
      
      <!-- 文件列表表格 -->
      <el-table
        :data="files"
        v-loading="loading"
        style="width: 100%; margin-top: 20px"
      >
        <el-table-column prop="instanceName" label="实例" width="150" />
        <el-table-column prop="fileName" label="文件名" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.fileName" placement="top">
              <span class="file-name">{{ row.fileName }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="fileSize" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.fileSize) }}
          </template>
        </el-table-column>
        <el-table-column prop="parseStatus" label="解析状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getParseStatusType(row.parseStatus)">
              {{ getParseStatusText(row.parseStatus) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="parsedCount" label="解析数量" width="100">
          <template #default="{ row }">
            {{ row.parsedCount || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="analyzeStatus" label="分析状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getAnalyzeStatusType(row.analyzeStatus)">
              {{ getAnalyzeStatusText(row.analyzeStatus) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="analyzedCount" label="分析数量" width="100">
          <template #default="{ row }">
            {{ row.analyzedCount || 0 }}
          </template>
        </el-table-column>
        <el-table-column prop="suggestionCount" label="建议数" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.suggestionCount > 0" type="warning">
              {{ row.suggestionCount }}
            </el-tag>
            <span v-else>0</span>
          </template>
        </el-table-column>
        <el-table-column prop="uploadedBy" label="上传者" width="100" />
        <el-table-column prop="createdAt" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.createdAt) }}
          </template>
        </el-table-column>
        <el-table-column prop="expireAt" label="过期时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.expireAt) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.parseStatus === 'completed' && row.analyzeStatus !== 'analyzing'"
              type="primary"
              size="small"
              link
              @click="handleAnalyze(row)"
            >
              分析
            </el-button>
            <el-button
              type="info"
              size="small"
              link
              @click="handleViewDetail(row)"
            >
              详情
            </el-button>
            <el-button
              type="danger"
              size="small"
              link
              @click="handleDelete(row)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="文件详情"
      width="60%"
      destroy-on-close
    >
      <el-descriptions :column="2" border v-if="currentFile">
        <el-descriptions-item label="实例">
          {{ currentFile.instanceName }}
        </el-descriptions-item>
        <el-descriptions-item label="文件名">
          {{ currentFile.fileName }}
        </el-descriptions-item>
        <el-descriptions-item label="文件大小">
          {{ formatFileSize(currentFile.fileSize) }}
        </el-descriptions-item>
        <el-descriptions-item label="文件哈希">
          <el-tooltip :content="currentFile.fileHash" placement="top">
            <span class="hash-text">{{ currentFile.fileHash }}</span>
          </el-tooltip>
        </el-descriptions-item>
        <el-descriptions-item label="解析状态">
          <el-tag :type="getParseStatusType(currentFile.parseStatus)">
            {{ getParseStatusText(currentFile.parseStatus) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="分析状态">
          <el-tag :type="getAnalyzeStatusType(currentFile.analyzeStatus)">
            {{ getAnalyzeStatusText(currentFile.analyzeStatus) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="解析数量">
          {{ currentFile.parsedCount || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="分析数量">
          {{ currentFile.analyzedCount || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="建议数量">
          {{ currentFile.suggestionCount || 0 }}
        </el-descriptions-item>
        <el-descriptions-item label="上传者">
          {{ currentFile.uploadedBy }}
        </el-descriptions-item>
        <el-descriptions-item label="上传时间">
          {{ formatTime(currentFile.createdAt) }}
        </el-descriptions-item>
        <el-descriptions-item label="过期时间">
          {{ formatTime(currentFile.expireAt) }}
        </el-descriptions-item>
        <el-descriptions-item label="解析错误" :span="2" v-if="currentFile.parseError">
          <el-alert type="error" :closable="false">
            {{ currentFile.parseError }}
          </el-alert>
        </el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { UploadFilled, Upload } from '@element-plus/icons-vue'
import request from '@/utils/request'
import dayjs from 'dayjs'

// 表单相关
const formRef = ref(null)
const uploadRef = ref(null)
const uploading = ref(false)
const fileList = ref([])

const uploadForm = reactive({
  instanceId: null,
  autoAnalyze: true
})

const rules = {
  instanceId: [{ required: true, message: '请选择实例', trigger: 'change' }],
  file: [{ required: true, message: '请选择文件', trigger: 'change' }]
}

// 实例列表
const instances = ref([])

// 文件列表
const loading = ref(false)
const files = ref([])

const filters = reactive({
  instanceId: null,
  parseStatus: null,
  analyzeStatus: null
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

// 详情对话框
const detailDialogVisible = ref(false)
const currentFile = ref(null)

// 文件选择变化
const handleFileChange = (file, fileList) => {
  // 检查文件大小
  const maxSize = 50 * 1024 * 1024 // 50MB
  if (file.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB')
    fileList.pop()
    return
  }
  fileList.value = [file]
}

// 文件移除
const handleFileRemove = (file, fileList) => {
  fileList.value = []
}

// 上传文件
const handleUpload = async () => {
  if (!uploadForm.instanceId) {
    ElMessage.warning('请选择实例')
    return
  }
  
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择文件')
    return
  }
  
  uploading.value = true
  
  try {
    const formData = new FormData()
    formData.append('file', fileList.value[0].raw)
    
    const response = await request.post(
      `/api/v1/sql-optimization/upload-slow-log?instance_id=${uploadForm.instanceId}&auto_analyze=${uploadForm.autoAnalyze}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      }
    )
    
    ElMessage.success('上传成功')
    resetForm()
    fetchFiles()
    
  } catch (error) {
    console.error('上传失败:', error)
    ElMessage.error(error.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

// 重置表单
const resetForm = () => {
  uploadForm.instanceId = null
  uploadForm.autoAnalyze = true
  fileList.value = []
  uploadRef.value?.clearFiles()
}

// 获取实例列表
const fetchInstances = async () => {
  try {
    const response = await request.get('/api/v1/instances', {
      params: {
        page: 1,
        page_size: 100
      }
    })
    instances.value = response.data.items || []
  } catch (error) {
    console.error('获取实例列表失败:', error)
  }
}

// 获取文件列表
const fetchFiles = async () => {
  loading.value = true
  
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize
    }
    
    if (filters.instanceId) {
      params.instance_id = filters.instanceId
    }
    if (filters.parseStatus) {
      params.parse_status = filters.parseStatus
    }
    if (filters.analyzeStatus) {
      params.analyze_status = filters.analyzeStatus
    }
    
    const response = await request.get('/api/v1/sql-optimization/slow-log-files', {
      params
    })
    
    files.value = response.data.items || []
    pagination.total = response.data.total || 0
    
  } catch (error) {
    console.error('获取文件列表失败:', error)
    // 404 错误不显示提示
    if (error.response?.status !== 404) {
      ElMessage.error('获取文件列表失败')
    }
    files.value = []
    pagination.total = 0
  } finally {
    loading.value = false
  }
}

// 筛选处理
const handleFilter = () => {
  pagination.page = 1
  fetchFiles()
}

// 分页处理
const handlePageChange = (page) => {
  pagination.page = page
  fetchFiles()
}

const handlePageSizeChange = (size) => {
  pagination.pageSize = size
  pagination.page = 1
  fetchFiles()
}

// 分析文件
const handleAnalyze = async (row) => {
  try {
    ElMessage.info('开始分析...')
    const response = await request.post(
      `/api/v1/sql-optimization/slow-log-files/${row.id}/analyze`
    )
    ElMessage.success(`分析完成，发现 ${response.data.suggestion_count || 0} 个问题`)
    fetchFiles()
  } catch (error) {
    console.error('分析失败:', error)
    ElMessage.error(error.response?.data?.detail || '分析失败')
  }
}

// 查看详情
const handleViewDetail = (row) => {
  currentFile.value = row
  detailDialogVisible.value = true
}

// 删除文件
const handleDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除该文件吗？关联的分析历史也会被删除。',
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await request.delete(`/api/v1/sql-optimization/slow-log-files/${row.id}`)
    ElMessage.success('删除成功')
    fetchFiles()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除失败')
    }
  }
}

// 格式化文件大小
const formatFileSize = (bytes) => {
  if (!bytes) return '0 B'
  
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + sizes[i]
}

// 格式化时间
const formatTime = (time) => {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-'
}

// 获取解析状态类型
const getParseStatusType = (status) => {
  const types = {
    pending: 'info',
    parsing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取解析状态文本
const getParseStatusText = (status) => {
  const texts = {
    pending: '待解析',
    parsing: '解析中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

// 获取分析状态类型
const getAnalyzeStatusType = (status) => {
  const types = {
    pending: 'info',
    analyzing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

// 获取分析状态文本
const getAnalyzeStatusText = (status) => {
  const texts = {
    pending: '待分析',
    analyzing: '分析中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

// 暴露方法给父组件
defineExpose({
  fetchData: fetchFiles
})

onMounted(() => {
  fetchInstances()
  fetchFiles()
})
</script>

<style scoped>
.file-upload {
  padding: 0;
}

.upload-card,
.file-list-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.upload-dragger {
  width: 100%;
}

.form-tip {
  margin-left: 10px;
  color: #909399;
  font-size: 12px;
}

.filter-bar {
  display: flex;
  align-items: center;
}

.file-name {
  display: inline-block;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.hash-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
