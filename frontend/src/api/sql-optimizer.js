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

  // 分析SQL
  analyze(data) {
    return request.post('/sql-optimizer/analyze', data)
  },

  // 获取分析历史
  getHistory(instanceId, limit = 20) {
    return request.get(`/sql-optimizer/history/${instanceId}`, { params: { limit } })
  },

  // 获取分析详情
  getHistoryDetail(historyId) {
    return request.get(`/sql-optimizer/history/detail/${historyId}`)
  }
}
