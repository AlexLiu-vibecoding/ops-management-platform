<template>
  <div class="slow-query-monitor">
    <el-tabs v-model="activeTab" type="border-card" @tab-change="handleTabChange">
      <!-- 慢查询列表 -->
      <el-tab-pane label="慢查询列表" name="list">
        <SlowQueryList ref="slowQueryListRef" @analyze="handleAnalyze" />
      </el-tab-pane>
      
      <!-- 优化建议 -->
      <el-tab-pane label="优化建议" name="suggestions">
        <OptimizationSuggestions ref="suggestionsRef" />
      </el-tab-pane>
      
      <!-- 采集任务 -->
      <el-tab-pane label="采集任务" name="tasks">
        <CollectionTasks ref="tasksRef" />
      </el-tab-pane>
      
      <!-- 分析历史 -->
      <el-tab-pane label="分析历史" name="history">
        <AnalysisHistory ref="historyRef" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import SlowQueryList from './SlowQueryList.vue'
import OptimizationSuggestions from './OptimizationSuggestions.vue'
import CollectionTasks from './CollectionTasks.vue'
import AnalysisHistory from './AnalysisHistory.vue'

const router = useRouter()
const activeTab = ref('list')

// 子组件引用
const slowQueryListRef = ref(null)
const suggestionsRef = ref(null)
const tasksRef = ref(null)
const historyRef = ref(null)

// 标签页切换
const handleTabChange = (name) => {
  // 切换标签页时刷新数据
  switch (name) {
    case 'list':
      slowQueryListRef.value?.fetchData()
      break
    case 'suggestions':
      suggestionsRef.value?.fetchData()
      break
    case 'tasks':
      tasksRef.value?.fetchData()
      break
    case 'history':
      historyRef.value?.fetchData()
      break
  }
}

// 处理分析事件
const handleAnalyze = (row) => {
  // 可以跳转到分析详情或打开分析对话框
  console.log('Analyze slow query:', row)
}

onMounted(() => {
  // 从 URL 参数恢复标签页状态
  const tab = router.currentRoute.value.query.tab
  if (tab && ['list', 'suggestions', 'tasks', 'history'].includes(tab)) {
    activeTab.value = tab
  }
})
</script>

<style lang="scss" scoped>
.slow-query-monitor {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 100px);
  
  :deep(.el-tabs__content) {
    padding: 0;
    
    .el-tab-pane {
      background: white;
    }
  }
  
  :deep(.el-tabs--border-card) {
    border-radius: 4px;
    box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
    
    > .el-tabs__header {
      background: #f5f7fa;
      border-bottom: 1px solid #e4e7ed;
      margin: 0;
      
      .el-tabs__item {
        height: 45px;
        line-height: 45px;
        
        &.is-active {
          background: white;
        }
      }
    }
  }
}
</style>
