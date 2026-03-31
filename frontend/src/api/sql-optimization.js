import request from './index'

/**
 * SQL 优化闭环 API
 */
export const sqlOptimizationApi = {
  // ==================== 采集任务管理 ====================

  /**
   * 获取采集任务列表
   */
  getTasks(params = {}) {
    return request.get('/sql-optimization/tasks', { params })
  },

  /**
   * 创建采集任务
   */
  createTask(data) {
    return request.post('/sql-optimization/tasks', data)
  },

  /**
   * 获取采集任务详情
   */
  getTask(taskId) {
    return request.get(`/sql-optimization/tasks/${taskId}`)
  },

  /**
   * 更新采集任务
   */
  updateTask(taskId, data) {
    return request.put(`/sql-optimization/tasks/${taskId}`, data)
  },

  /**
   * 删除采集任务
   */
  deleteTask(taskId) {
    return request.delete(`/sql-optimization/tasks/${taskId}`)
  },

  /**
   * 手动触发采集
   */
  runTask(taskId) {
    return request.post(`/sql-optimization/tasks/${taskId}/run`)
  },

  // ==================== 优化建议管理 ====================

  /**
   * 获取优化建议列表
   */
  getSuggestions(params = {}) {
    return request.get('/sql-optimization/suggestions', { params })
  },

  /**
   * 获取优化建议详情
   */
  getSuggestion(suggestionId) {
    return request.get(`/sql-optimization/suggestions/${suggestionId}`)
  },

  /**
   * 采用建议
   */
  adoptSuggestion(suggestionId) {
    return request.post(`/sql-optimization/suggestions/${suggestionId}/adopt`)
  },

  /**
   * 拒绝建议
   */
  rejectSuggestion(suggestionId, reason = '') {
    return request.post(`/sql-optimization/suggestions/${suggestionId}/reject`, { reason })
  },

  /**
   * 验证优化效果
   */
  verifySuggestion(suggestionId) {
    return request.post(`/sql-optimization/suggestions/${suggestionId}/verify`)
  },

  /**
   * 手动分析 SQL
   */
  analyzeSql(data) {
    return request.post('/sql-optimization/suggestions/analyze', data, {
      timeout: 120000  // 2 分钟超时（LLM 分析可能较慢）
    })
  }
}

export default sqlOptimizationApi
