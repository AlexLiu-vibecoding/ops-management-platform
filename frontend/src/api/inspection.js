import request from './index'

// 定时巡检API
export const scheduledInspectionApi = {
  // 获取任务列表
  list(params) {
    return request.get('/scheduled-inspections', { params })
  },

  // 获取任务详情
  get(id) {
    return request.get(`/scheduled-inspections/${id}`)
  },

  // 创建任务
  create(data) {
    return request.post('/scheduled-inspections', data)
  },

  // 更新任务
  update(id, data) {
    return request.put(`/scheduled-inspections/${id}`, data)
  },

  // 删除任务
  delete(id) {
    return request.delete(`/scheduled-inspections/${id}`)
  },

  // 启用/禁用任务
  toggle(id) {
    return request.post(`/scheduled-inspections/${id}/toggle`)
  },

  // 手动执行任务
  run(id) {
    return request.post(`/scheduled-inspections/${id}/run`)
  },

  // 验证Cron表达式
  validateCron(cronExpression) {
    return request.post('/scheduled-inspections/validate-cron', null, {
      params: { cron_expression: cronExpression }
    })
  },

  // 获取模块列表
  getModules() {
    return request.get('/scheduled-inspections/modules/list')
  },

  // 获取执行记录列表
  getExecutions(taskId, params) {
    return request.get(`/scheduled-inspections/${taskId}/executions`, { params })
  },

  // 获取执行记录详情
  getExecution(executionId) {
    return request.get(`/scheduled-inspections/executions/${executionId}`)
  }
}

// 告警规则API
export const alertRulesApi = {
  // 获取规则列表
  list(params) {
    return request.get('/alert-rules', { params })
  },

  // 获取规则详情
  get(id) {
    return request.get(`/alert-rules/${id}`)
  },

  // 创建规则
  create(data) {
    return request.post('/alert-rules', data)
  },

  // 更新规则
  update(id, data) {
    return request.put(`/alert-rules/${id}`, data)
  },

  // 删除规则
  delete(id) {
    return request.delete(`/alert-rules/${id}`)
  },

  // 启用/禁用规则
  toggle(id) {
    return request.post(`/alert-rules/${id}/toggle`)
  },

  // 获取规则类型列表
  getTypes() {
    return request.get('/alert-rules/types/list')
  },

  // 获取运算符列表
  getOperators() {
    return request.get('/alert-rules/operators/list')
  },

  // 获取聚合方式列表
  getAggregations() {
    return request.get('/alert-rules/aggregations/list')
  },

  // 获取告警级别列表
  getSeverities() {
    return request.get('/alert-rules/severities/list')
  }
}

// 变更时间窗口API
export const changeWindowsApi = {
  // 获取窗口列表
  list(params) {
    return request.get('/change-windows', { params })
  },

  // 获取窗口详情
  get(id) {
    return request.get(`/change-windows/${id}`)
  },

  // 创建窗口
  create(data) {
    return request.post('/change-windows', data)
  },

  // 更新窗口
  update(id, data) {
    return request.put(`/change-windows/${id}`, data)
  },

  // 删除窗口
  delete(id) {
    return request.delete(`/change-windows/${id}`)
  },

  // 启用/禁用窗口
  toggle(id) {
    return request.post(`/change-windows/${id}/toggle`)
  },

  // 检查是否在变更窗口内
  check(environmentId, checkTime) {
    return request.post('/change-windows/check', null, {
      params: { 
        environment_id: environmentId,
        check_time: checkTime 
      }
    })
  }
}
