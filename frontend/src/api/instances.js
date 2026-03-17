import request from './index'

export const instancesApi = {
  // 获取实例列表
  getList(params) {
    return request.get('/instances', { params })
  },

  // 获取实例详情
  getDetail(id) {
    return request.get(`/instances/${id}`)
  },

  // 创建实例
  create(data) {
    return request.post('/instances', data)
  },

  // 更新实例
  update(id, data) {
    return request.put(`/instances/${id}`, data)
  },

  // 删除实例
  delete(id) {
    return request.delete(`/instances/${id}`)
  },

  // 测试连接
  testConnection(data) {
    return request.post('/instances/test', data)
  },

  // 检查状态
  checkStatus(id) {
    return request.post(`/instances/${id}/check`)
  },

  // 获取实例变量
  getVariables(id) {
    return request.get(`/instances/${id}/variables`)
  },

  // 获取数据库列表
  getDatabases(id) {
    return request.get(`/instances/${id}/databases`)
  },

  // 获取表列表
  getTables(id, database) {
    return request.get(`/instances/${id}/databases/${database}/tables`)
  },

  // 获取分组列表
  getGroups() {
    return request.get('/instances/groups/')
  },

  // 创建分组
  createGroup(data) {
    return request.post('/instances/groups/', null, { params: data })
  }
}
