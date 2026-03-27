import request from './index'

export const permissionApi = {
  /**
   * 获取当前用户权限
   */
  getPermissions() {
    return request.get('/batch/permissions')
  },
  
  /**
   * 批量操作实例
   */
  batchInstances(action, ids) {
    return request.post('/batch/instances', { action, ids })
  },
  
  /**
   * 批量操作环境
   */
  batchEnvironments(action, ids) {
    return request.post('/batch/environments', { action, ids })
  },
  
  /**
   * 批量操作变更
   */
  batchApprovals(action, ids) {
    return request.post('/batch/approvals', { action, ids })
  }
}
