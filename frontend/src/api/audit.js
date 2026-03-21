import request from './index'

export const auditApi = {
  // 获取审计日志列表
  getLogs(params) {
    return request.get('/audit/logs', { params })
  },

  // 获取审计日志详情
  getDetail(id) {
    return request.get(`/audit/logs/${id}`)
  },

  // 获取操作类型列表
  getOperationTypes() {
    return request.get('/audit/operation-types')
  },

  // 导出审计日志
  exportLogs(params) {
    return request.get('/audit/export', { 
      params,
      responseType: 'blob'
    })
  }
}
