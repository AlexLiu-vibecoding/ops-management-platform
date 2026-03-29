import request from './index'

export const sqlOptimizerApi = {
  // 同步表结构
  syncSchema(data) {
    return request.post('/sql-optimizer/sync-schema', data)
  },

  // 获取表结构列表
  getSchemas(instanceId, database = null) {
    const params = database ? { database } : {}
    return request.get(`/sql-optimizer/schemas/${instanceId}`, { params })
  },

  // 分析SQL（需要更长超时时间，因为包含 LLM 调用）
  analyze(data) {
    return request.post('/sql-optimizer/analyze', data, {
      timeout: 120000  // 2 分钟超时
    })
  },

  // 获取分析历史
  getHistory(instanceId, limit = 10) {
    return request.get(`/sql-optimizer/history/${instanceId}`, { params: { limit } })
  },

  // 清空分析历史
  clearHistory(instanceId) {
    return request.delete(`/sql-optimizer/history/${instanceId}`)
  },

  // 获取分析详情
  getHistoryDetail(historyId) {
    return request.get(`/sql-optimizer/history/detail/${historyId}`)
  }
}
