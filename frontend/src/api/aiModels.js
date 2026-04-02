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

  // 获取支持的提供商列表
  getProviders() {
    return request.get('/ai-models/providers')
  },

  // 获取场景列表
  getScenes() {
    return request.get('/ai-models/scenes')
  },

  // 获取预设模板列表
  getTemplates() {
    return request.get('/ai-models/templates')
  },

  // ========== 可用模型 ==========

  // 获取可用模型列表
  getAvailableModels(provider = null) {
    const params = provider ? { provider } : {}
    return request.get('/ai-models/available-models', { params })
  },

  // 刷新可用模型列表
  refreshAvailableModels() {
    return request.post('/ai-models/available-models/refresh')
  },

  // ========== 场景配置 ==========
  
  // 获取所有场景配置
  getSceneConfigs() {
    return request.get('/ai-models/scene-configs/list')
  },

  // 获取单个场景配置
  getSceneConfig(scene) {
    return request.get(`/ai-models/scene-configs/${scene}`)
  },

  // 更新场景配置
  updateSceneConfig(scene, data) {
    return request.put(`/ai-models/scene-configs/${scene}`, data)
  },

  // 获取调用统计
  getCallStats(days = 7) {
    return request.get('/ai-models/stats/call-logs', { params: { days } })
  },

  // 兼容旧 API
  getUseCases() {
    return request.get('/ai-models/scenes')
  }
}
