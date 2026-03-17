import request from './index'

export const authApi = {
  // 登录
  login(data) {
    return request.post('/auth/login', data)
  },

  // 获取当前用户信息
  getCurrentUser() {
    return request.get('/auth/me')
  },

  // 修改密码
  changePassword(oldPassword, newPassword) {
    return request.put('/auth/password', null, {
      params: { old_password: oldPassword, new_password: newPassword }
    })
  },

  // 登出
  logout() {
    return request.post('/auth/logout')
  }
}
