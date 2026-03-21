<template>
  <el-dropdown trigger="click" @command="handleCommand">
    <span class="lang-switch">
      <el-icon><Compass /></el-icon>
      <span class="lang-text">{{ currentLangLabel }}</span>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item 
          v-for="lang in languages" 
          :key="lang.value" 
          :command="lang.value"
          :class="{ 'is-active': currentLang === lang.value }"
        >
          {{ lang.label }}
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Compass } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const { locale } = useI18n()

const languages = [
  { value: 'zh', label: '中文' },
  { value: 'en', label: 'English' }
]

const currentLang = computed(() => locale.value)

const currentLangLabel = computed(() => {
  const lang = languages.find(l => l.value === currentLang.value)
  return lang ? lang.label : '中文'
})

const handleCommand = (lang) => {
  if (lang !== locale.value) {
    locale.value = lang
    localStorage.setItem('language', lang)
    document.documentElement.setAttribute('lang', lang)
    
    // 提示需要刷新页面以应用 Element Plus 语言
    ElMessage.success(lang === 'zh' ? '语言已切换，刷新页面生效' : 'Language changed, refresh to apply')
    
    // 刷新页面以应用 Element Plus 语言
    setTimeout(() => {
      window.location.reload()
    }, 500)
  }
}
</script>

<style lang="scss" scoped>
.lang-switch {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 0 8px;
  height: 100%;
  
  &:hover {
    color: var(--el-color-primary);
  }
  
  .lang-text {
    font-size: 14px;
  }
}

.is-active {
  color: var(--el-color-primary);
  font-weight: 500;
}
</style>
