import request from './index'

export const monitorApi = {
  // 获取全局监控开关
  getGlobalSwitches() {
    return request.get('/monitor/switches/global')
  },

  // 更新全局监控开关
  updateGlobalSwitch(data) {
    return request.put('/monitor/switches/global', data)
  },

  // 获取实例监控开关
  getInstanceSwitches(instanceId) {
    return request.get(`/monitor/switches/instance/${instanceId}`)
  },

  // 更新实例监控开关
  updateInstanceSwitch(instanceId, monitorType, data) {
    return request.put(`/monitor/switches/instance/${instanceId}/${monitorType}`, data)
  },

  // 获取监控配置
  getConfig() {
    return request.get('/monitor/config')
  },

  // 更新监控配置
  updateConfig(data) {
    return request.put('/monitor/config', data)
  },

  // 慢查询监控配置
  getSlowQueryConfig() {
    return request.get('/monitor/slow-query/config')
  },

  updateSlowQueryConfig(data) {
    return request.put('/monitor/slow-query/config', data)
  },

  getSlowQueryStatistics(hours = 24) {
    return request.get('/monitor/slow-query/statistics', { params: { hours } })
  },

  // 高CPU SQL监控配置
  getHighCpuConfig() {
    return request.get('/monitor/high-cpu/config')
  },

  updateHighCpuConfig(data) {
    return request.put('/monitor/high-cpu/config', data)
  },

  getHighCpuStatistics(hours = 24) {
    return request.get('/monitor/high-cpu/statistics', { params: { hours } })
  },

  // 监控总览
  getOverview() {
    return request.get('/monitor/overview')
  },

  // 性能监控
  performance: {
    getCurrent(instanceId) {
      return request.get(`/performance/${instanceId}/current`)
    },
    getHistory(instanceId, hours = 1) {
      return request.get(`/performance/${instanceId}/history`, { params: { hours } })
    },
    getStatistics(instanceId, hours = 24) {
      return request.get(`/performance/${instanceId}/statistics`, { params: { hours } })
    },
    getOverview() {
      return request.get('/performance/overview')
    }
  },

  // 慢查询监控
  slowQuery: {
    getList(instanceId, params) {
      return request.get(`/slow-query/${instanceId}`, { params })
    },
    getTop(instanceId, hours = 24, topN = 10) {
      return request.get(`/slow-query/${instanceId}/top`, { params: { hours, top_n: topN } })
    },
    getStatistics(instanceId, hours = 24) {
      return request.get(`/slow-query/${instanceId}/statistics`, { params: { hours } })
    },
    // 分析慢查询（需要更长超时时间，因为包含 LLM 调用）
    analyze(instanceId, queryId) {
      return request.get(`/slow-query/${instanceId}/analysis/${queryId}`, {
        timeout: 120000  // 2 分钟超时
      })
    }
  }
}
