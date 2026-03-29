<template>
  <div class="table-actions">
    <!-- 主要操作按钮 -->
    <el-button 
      v-for="action in primaryActions" 
      :key="action.key"
      link 
      type="primary" 
      size="small"
      @click="$emit(action.event, row)"
    >
      {{ action.label }}
    </el-button>
    
    <!-- 次要操作：更多下拉菜单 -->
    <el-dropdown 
      v-if="secondaryActions.length > 0" 
      trigger="click"
      @command="(cmd) => $emit(cmd, row)"
    >
      <el-button link type="primary" size="small" class="more-btn">
        更多
        <el-icon class="el-icon--right"><ArrowDown /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item 
            v-for="action in secondaryActions" 
            :key="action.key"
            :command="action.event"
            :divided="action.divided"
            :class="action.danger ? 'danger-item' : ''"
          >
            <el-icon v-if="action.icon"><component :is="action.icon" /></el-icon>
            {{ action.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  row: {
    type: Object,
    required: true
  },
  actions: {
    type: Array,
    required: true
    // 格式: [{ key, label, event, primary?, icon?, danger?, divided?, visible? }]
  },
  maxPrimary: {
    type: Number,
    default: 2
  }
})

defineEmits(['view', 'edit', 'delete', 'test', 'enable', 'disable', 'export', 'copy', 'approve', 'reject', 'execute', 'revoke'])

// 过滤可见的操作
const visibleActions = computed(() => {
  return props.actions.filter(action => {
    if (typeof action.visible === 'function') {
      return action.visible(props.row)
    }
    return action.visible !== false
  })
})

// 主要操作按钮（前 maxPrimary 个）
const primaryActions = computed(() => {
  return visibleActions.value
    .filter(a => a.primary !== false)
    .slice(0, props.maxPrimary)
})

// 次要操作（下拉菜单）
const secondaryActions = computed(() => {
  const primaryKeys = primaryActions.value.map(a => a.key)
  return visibleActions.value.filter(a => !primaryKeys.includes(a.key))
})
</script>

<style lang="scss" scoped>
.table-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  
  .more-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    
    .el-icon--right {
      font-size: 12px;
      margin-left: 2px;
    }
  }
}

:deep(.el-dropdown-menu__item) {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  
  .el-icon {
    font-size: 14px;
  }
  
  &.danger-item {
    color: var(--el-color-danger);
    
    &:hover {
      background-color: var(--el-color-danger-light-9);
    }
  }
}
</style>
