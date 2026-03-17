import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import router from '@/router'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(JSON.parse(localStorage.getItem('user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'super_admin')

  async function login(username, password) {
    try {
      const res = await authApi.login({ username, password })
      token.value = res.access_token
      user.value = res.user
      localStorage.setItem('token', res.access_token)
      localStorage.setItem('user', JSON.stringify(res.user))
      return { success: true }
    } catch (error) {
      return { success: false, message: error.response?.data?.detail || '登录失败' }
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    router.push('/login')
  }

  function checkAuth() {
    if (token.value && !user.value) {
      // 有token但没有用户信息，尝试获取
      authApi.getCurrentUser()
        .then(res => {
          user.value = res
          localStorage.setItem('user', JSON.stringify(res))
        })
        .catch(() => {
          logout()
        })
    }
  }

  return {
    token,
    user,
    isLoggedIn,
    isAdmin,
    login,
    logout,
    checkAuth
  }
})
