import request from './index'

export const notificationApi = {
  // ============ 通道管理 ============
  
  // 获取通道列表
  getChannels(params) {
    return request.get('/notification/channels', { params })
  },

  // 获取通道类型列表
  getChannelTypes() {
    return request.get('/notification/channels/channel-types')
  },

  // 获取通道详情
  getChannelDetail(id) {
    return request.get(`/notification/channels/detail/${id}`)
  },

  // 创建通道
  createChannel(data) {
    return request.post('/notification/channels', data)
  },

  // 更新通道
  updateChannel(id, data) {
    return request.put(`/notification/channels/detail/${id}`, data)
  },

  // 删除通道
  deleteChannel(id) {
    return request.delete(`/notification/channels/detail/${id}`)
  },

  // 测试通道
  testChannel(id) {
    return request.post(`/notification/channels/detail/${id}/test`)
  },

  // ============ 静默规则 ============

  // 获取通道的静默规则列表
  getSilenceRules(channelId, params) {
    return request.get(`/notification/channels/${channelId}/silence-rules`, { params })
  },

  // 创建静默规则
  createSilenceRule(channelId, data) {
    return request.post(`/notification/channels/${channelId}/silence-rules`, data)
  },

  // 更新静默规则
  updateSilenceRule(channelId, ruleId, data) {
    return request.put(`/notification/channels/${channelId}/silence-rules/${ruleId}`, data)
  },

  // 删除静默规则
  deleteSilenceRule(channelId, ruleId) {
    return request.delete(`/notification/channels/${channelId}/silence-rules/${ruleId}`)
  },

  // ============ 通道绑定 ============

  // 获取通道的绑定列表
  getChannelBindings(channelId, params) {
    return request.get(`/notification/channels/${channelId}/bindings`, { params })
  },

  // 创建绑定
  createChannelBinding(channelId, data) {
    return request.post(`/notification/channels/${channelId}/bindings`, data)
  },

  // 删除绑定
  deleteChannelBinding(channelId, bindingId) {
    return request.delete(`/notification/channels/${channelId}/bindings/${bindingId}`)
  }
}
