import request from './index'

export const notificationApi = {
  // ============ 通道管理 ============
  
  // 获取通道列表
  getChannels(params) {
    return request.get('/notification/channels', { params })
  },

  // 获取通道类型列表
  getChannelTypes() {
    return request.get('/notification/channels/types')
  },

  // 获取通道详情
  getChannelDetail(id) {
    return request.get(`/notification/channels/${id}`)
  },

  // 创建通道
  createChannel(data) {
    return request.post('/notification/channels', data)
  },

  // 更新通道
  updateChannel(id, data) {
    return request.put(`/notification/channels/${id}`, data)
  },

  // 删除通道
  deleteChannel(id) {
    return request.delete(`/notification/channels/${id}`)
  },

  // 测试通道
  testChannel(id) {
    return request.post(`/notification/channels/${id}/test`)
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

  // ============ 频率限制 ============

  // 获取通道的频率限制列表
  getRateLimits(channelId, params) {
    return request.get(`/notification/channels/${channelId}/rate-limits`, { params })
  },

  // 创建频率限制
  createRateLimit(channelId, data) {
    return request.post(`/notification/channels/${channelId}/rate-limits`, data)
  },

  // 更新频率限制
  updateRateLimit(channelId, ruleId, data) {
    return request.put(`/notification/channels/${channelId}/rate-limits/${ruleId}`, data)
  },

  // 删除频率限制
  deleteRateLimit(channelId, ruleId) {
    return request.delete(`/notification/channels/${channelId}/rate-limits/${ruleId}`)
  }
}
