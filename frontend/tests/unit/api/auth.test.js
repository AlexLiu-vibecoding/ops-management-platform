/**
 * 认证 API 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'

// 模拟 API 模块
const mockAuthApi = {
  async login(credentials) {
    const response = await fetch('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials)
    })
    return response.json()
  },

  async getCurrentUser() {
    const token = localStorage.getItem('token')
    const response = await fetch('/api/v1/auth/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    return response.json()
  },

  logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
  }
}

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn()
    global.localStorage = {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn()
    }
  })

  describe('login', () => {
    it('应该成功登录并返回 token', async () => {
      const mockResponse = {
        access_token: 'test_token',
        user: { id: 1, username: 'admin' }
      }
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockResponse)
      })

      const result = await mockAuthApi.login({
        username: 'admin',
        password: 'admin123'
      })

      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: 'admin', password: 'admin123' })
      })
    })

    it('应该处理登录失败', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: '用户名或密码错误' })
      })

      const result = await mockAuthApi.login({
        username: 'wrong',
        password: 'wrong'
      })

      expect(result).toEqual({ detail: '用户名或密码错误' })
    })
  })

  describe('logout', () => {
    it('应该清除本地存储的 token', () => {
      mockAuthApi.logout()
      
      expect(localStorage.removeItem).toHaveBeenCalledWith('token')
      expect(localStorage.removeItem).toHaveBeenCalledWith('user')
    })
  })

  describe('getCurrentUser', () => {
    it('应该获取当前用户信息', async () => {
      const mockUser = { id: 1, username: 'admin', role: 'super_admin' }
      
      localStorage.getItem.mockReturnValue('test_token')
      fetch.mockResolvedValueOnce({
        json: () => Promise.resolve(mockUser)
      })

      const result = await mockAuthApi.getCurrentUser()

      expect(result).toEqual(mockUser)
      expect(fetch).toHaveBeenCalledWith('/api/v1/auth/me', {
        headers: { 'Authorization': 'Bearer test_token' }
      })
    })
  })
})
