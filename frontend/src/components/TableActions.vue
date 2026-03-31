<template>
  <div class="table-actions">
    <!-- 当操作数 <= 3 时，全部直接展示 -->
    <template v-if="shouldShowAll">
      <el-button 
        v-for="action in visibleActions" 
        :key="action.key"
        link 
        :type="action.danger ? 'danger' : 'primary'" 
        size="small"
        @click="$emit(action.event, row)"
      >
        {{ typeof action.label === 'function' ? action.label(row) : action.label }}
      </el-button>
    </template>
    
    <!-- 当操作数 > 3 时，主要按钮 + 更多下拉菜单 -->
    <template v-else>
      <!-- 主要操作按钮 -->
      <el-button 
        v-for="action in primaryActions" 
        :key="action.key"
        link 
        type="primary" 
        size="small"
        @click="$emit(action.event, row)"
      >
        {{ typeof action.label === 'function' ? action.label(row) : action.label }}
      </el-button>
      
      <!-- 次要操作：更多下拉菜单 -->
      <el-dropdown 
        v-if="secondaryActions.length > 0" 
        trigger="click"
        teleported
        :popper-options="{ modifiers: [{ name: 'flip', enabled: true }] }"
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
              {{ typeof action.label === 'function' ? action.label(row) : action.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </template>
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
  },
  // 当操作数 <= 此值时，全部直接展示
  showAllThreshold: {
    type: Number,
    default: 3
  }
})

defineEmits(['view', 'edit', 'delete', 'test', 'enable', 'disable', 'export', 'copy', 'approve', 'reject', 'execute', 'revoke', 'trigger', 'pause', 'resume', 'history', 'duplicate', 'toggle'])

// 过滤可见的操作
const visibleActions = computed(() => {
  return props.actions.filter(action => {
    if (typeof action.visible === 'function') {
      return action.visible(props.row)
    }
    return action.visible !== false
  })
})

// 判断是否应该全部直接展示
const shouldShowAll = computed(() => {
  return visibleActions.value.length <= props.showAllThreshold
})

// 主要操作按钮
const primaryActions = computed(() => {
  // 按优先级排序：primary=true 的优先
  const sorted = [...visibleActions.value].sort((a, b) => {
    if (a.primary === true && b.primary !== true) return -1
    if (a.primary !== true && b.primary === true) return 1
    return 0
  })
  return sorted.slice(0, props.maxPrimary)
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
  flex-wrap: nowrap;
  white-space: nowrap;
  gap: 2px;
  min-width: fit-content;
  
  :deep(.el-button) {
    padding: 4px 8px;
    margin: 0;
    
    & + .el-button {
      margin-left: 0;
    }
  }
  
  .more-btn {
    display: flex;
    align-items: center;
    gap: 2px;
    flex-shrink: 0;
    
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
