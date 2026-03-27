<template>
  <div class="batch-action-bar" v-if="selectedCount > 0">
    <div class="selection-info">
      <el-checkbox 
        :model-value="isAllSelected" 
        :indeterminate="selectedCount > 0 && !isAllSelected"
        @change="$emit('select-all', $event)"
      />
      <span class="count">已选 {{ selectedCount }} 项</span>
      <el-button text type="primary" @click="$emit('clear-selection')">清除选择</el-button>
    </div>
    
    <div class="action-buttons">
      <template v-for="action in visibleActions" :key="action.key">
        <el-button
          :type="action.type || 'default'"
          :plain="action.plain !== false"
          :disabled="action.disabled"
          @click="handleAction(action)"
        >
          <el-icon v-if="action.icon"><component :is="action.icon" /></el-icon>
          {{ action.label }}
        </el-button>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'

const props = defineProps({
  selectedCount: {
    type: Number,
    default: 0
  },
  totalCount: {
    type: Number,
    default: 0
  },
  actions: {
    type: Array,
    default: () => []
  },
  permissions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['action', 'select-all', 'clear-selection'])

const isAllSelected = computed(() => {
  return props.selectedCount > 0 && props.selectedCount === props.totalCount
})

const visibleActions = computed(() => {
  return props.actions.filter(action => {
    if (action.permission && !props.permissions.includes(action.permission)) {
      return false
    }
    return true
  })
})

const handleAction = async (action) => {
  if (action.confirm !== false) {
    try {
      let confirmOptions = {
        confirmButtonText: action.confirmText || action.label,
        cancelButtonText: '取消',
        type: action.confirmType || 'warning'
      }
      
      // 需要输入确认的操作
      if (action.requireInput) {
        const { value } = await ElMessageBox.prompt(
          action.confirmMessage || `确定要${action.label}吗？`,
          '确认操作',
          {
            ...confirmOptions,
            inputPlaceholder: action.inputPlaceholder || `请输入 "${action.requireInput}" 确认`,
            inputValidator: (val) => val === action.requireInput || `请输入 ${action.requireInput}`
          }
        )
        emit('action', { action: action.key, confirmValue: value })
      } else {
        await ElMessageBox.confirm(
          action.confirmMessage || `确定要${action.label}选中的 ${props.selectedCount} 项吗？`,
          '确认操作',
          confirmOptions
        )
        emit('action', { action: action.key })
      }
    } catch {
      // 用户取消
    }
  } else {
    emit('action', { action: action.key })
  }
}
</script>

<style lang="scss" scoped>
.batch-action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: linear-gradient(135deg, #e8f4fd 0%, #f0f7ff 100%);
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  margin-bottom: 16px;
  
  .selection-info {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .count {
      font-weight: 500;
      color: #409eff;
    }
  }
  
  .action-buttons {
    display: flex;
    gap: 8px;
  }
}
</style>
