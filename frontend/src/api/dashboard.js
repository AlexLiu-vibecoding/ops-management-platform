import request from './index'

export const dashboardApi = {
  // 获取仪表盘统计数据
  getStats() {
    return request.get('/dashboard/stats')
  }
}
