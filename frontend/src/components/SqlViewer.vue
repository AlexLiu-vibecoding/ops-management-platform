<template>
  <div class="sql-viewer">
    <div class="sql-toolbar">
      <div class="sql-title">
        <el-icon v-if="titleIcon"><component :is="titleIcon" /></el-icon>
        <span>{{ title }}</span>
        <el-tag v-if="riskLevel" :type="getRiskTagType(riskLevel)" size="small">
          {{ getRiskLabel(riskLevel) }}
        </el-tag>
      </div>
      <div class="sql-actions">
        <el-button text size="small" @click="copySql" :disabled="!sql">
          <el-icon><DocumentCopy /></el-icon>
          复制
        </el-button>
      </div>
    </div>
    <div class="sql-content">
      <pre><code>{{ sql }}</code></pre>
    </div>
    <div v-if="warning" class="sql-warning">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ warning }}</span>
    </div>
  </div>
</template>

<script setup>
import { ElMessage } from 'element-plus'
import { DocumentCopy, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  title: {
    type: String,
    default: 'SQL内容'
  },
  titleIcon: {
    type: [Object, String],
    default: null
  },
  sql: {
    type: String,
    default: ''
  },
  riskLevel: {
    type: String,
    default: ''
  },
  warning: {
    type: String,
    default: ''
  }
})

const getRiskTagType = (level) => {
  const types = {
    low: 'success',
    medium: 'warning',
    high: 'danger',
    critical: 'danger'
  }
  return types[level] || 'info'
}

const getRiskLabel = (level) => {
  const labels = {
    low: '低风险',
    medium: '中风险',
    high: '高风险',
    critical: '极高风险'
  }
  return labels[level] || level
}

const copySql = async () => {
  try {
    await navigator.clipboard.writeText(props.sql)
    ElMessage.success('已复制到剪贴板')
  } catch (err) {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.sql-viewer {
  background: var(--el-fill-color-light);
  border-radius: 8px;
  overflow: hidden;
}

.sql-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: var(--el-fill-color);
  border-bottom: 1px solid var(--el-border-color-light);
}

.sql-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.sql-actions {
  display: flex;
  gap: 8px;
}

.sql-content {
  padding: 16px;
  overflow: auto;
  max-height: v-bind(maxHeight);
}

.sql-content.is-collapsed {
  max-height: 300px;
}

.sql-content pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-all;
}

.sql-content code {
  color: var(--el-text-color-primary);
}

.sql-warning {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
  font-size: 13px;
}
</style>
