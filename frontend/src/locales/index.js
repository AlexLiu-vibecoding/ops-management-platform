import { createI18n } from 'vue-i18n'
import zh from './zh'
import en from './en'

// 获取浏览器语言或本地存储的语言设置
function getDefaultLanguage() {
  const cached = localStorage.getItem('language')
  if (cached) {
    return cached
  }
  
  // 从浏览器语言推断
  const browserLang = navigator.language.toLowerCase()
  if (browserLang.startsWith('zh')) {
    return 'zh'
  }
  return 'en'
}

const i18n = createI18n({
  legacy: false, // 使用 Composition API 模式
  locale: getDefaultLanguage(),
  fallbackLocale: 'zh', // 回退语言
  messages: {
    zh,
    en
  }
})

// 切换语言并持久化
export function setLanguage(lang) {
  i18n.global.locale.value = lang
  localStorage.setItem('language', lang)
  // 设置 HTML lang 属性
  document.documentElement.setAttribute('lang', lang)
}

// 获取当前语言
export function getLanguage() {
  return i18n.global.locale.value
}

export default i18n
