/**
 * AI 模型配置 API
 */
import request from './index'

export const aiModelsApi = {
  // 获取模型配置列表
  getList(params = {}) {
    return request.get('/ai-models', { params })
  },

  // 获取单个模型配置
  getById(id) {
    return request.get(`/ai-models/${id}`)
  },

  // 创建模型配置
  create(data) {
    return request.post('/ai-models', data)
  },

  // 更新模型配置
  update(id, data) {
    return request.put(`/ai-models/${id}`, data)
  },

  // 删除模型配置
  delete(id) {
    return request.delete(`/ai-models/${id}`)
  },

  // 测试模型连接
  test(id, prompt) {
    return request.post(`/ai-models/${id}/test`, { prompt })
  },

  // 设为默认模型
  setDefault(id) {
    return request.post(`/ai-models/${id}/set-default`)
  },

  // 获取支持的提供商列表
  getProviders() {
    return request.get('/ai-models/providers')
  },

  // 获取使用场景列表
  getUseCases() {
    return request.get('/ai-models/use-cases')
  },

  // 获取预设模板列表
  getTemplates() {
    return request.get('/ai-models/templates')
  },

  // 获取调用统计
  getCallStats(days = 7) {
    return request.get('/ai-models/stats/call-logs', { params: { days } })
  }
}
