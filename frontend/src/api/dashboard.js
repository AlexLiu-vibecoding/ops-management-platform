import request from './index'

export const dashboardApi = {
  // 获取仪表盘统计数据
  getStats() {
    return request.get('/dashboard/stats')
  },
  
  // 获取待审批列表（用于待办事项）
  getPendingApprovals(limit = 5) {
    return request.get('/approvals', {
      params: {
        status_filter: 'pending',
        limit
      }
    }).then(data => data.items || [])
  }
}
