import request from './index'

export const usersApi = {
  // 获取用户列表
  getList(params) {
    return request.get('/users', { params })
  },

  // 获取用户详情
  getDetail(id) {
    return request.get(`/users/${id}`)
  },

  // 创建用户
  create(data) {
    return request.post('/users', data)
  },

  // 更新用户
  update(id, data) {
    return request.put(`/users/${id}`, data)
  },

  // 删除用户
  delete(id) {
    return request.delete(`/users/${id}`)
  },

  // 重置密码
  resetPassword(id, newPassword) {
    return request.post(`/users/${id}/reset-password`, null, {
      params: { new_password: newPassword }
    })
  },

  // 绑定环境权限
  bindEnvironments(id, environmentIds) {
    return request.post(`/users/${id}/environments`, environmentIds)
  }
}
