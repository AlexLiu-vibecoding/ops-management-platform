import request from './index'

export const dingtalkApi = {
  // ============ 钉钉通道 ============
  
  // 获取通道列表
  getChannels() {
    return request.get('/dingtalk/channels')
  },

  // 获取通道详情
  getChannelDetail(id) {
    return request.get(`/dingtalk/channels/${id}`)
  },

  // 创建通道
  createChannel(data) {
    return request.post('/dingtalk/channels', data)
  },

  // 更新通道
  updateChannel(id, data) {
    return request.put(`/dingtalk/channels/${id}`, data)
  },

  // 删除通道
  deleteChannel(id) {
    return request.delete(`/dingtalk/channels/${id}`)
  },

  // 测试通道
  testChannel(id, message) {
    return request.post(`/dingtalk/channels/${id}/test`, null, {
      params: { test_message: message }
    })
  },

  // ============ 通知绑定 ============

  // 获取绑定列表
  getBindings() {
    return request.get('/dingtalk/bindings')
  },

  // 创建绑定
  createBinding(data) {
    return request.post('/dingtalk/bindings', data)
  },

  // 删除绑定
  deleteBinding(id) {
    return request.delete(`/dingtalk/bindings/${id}`)
  }
}
