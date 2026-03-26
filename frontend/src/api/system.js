import request from './index'

export const systemApi = {
  // 获取系统概览
  getOverview() {
    return request.get('/system/overview')
  },

  // ==================== 数据库配置 ====================
  
  // 获取数据库类型配置
  getDatabaseConfig() {
    return request.get('/system/database-config')
  },

  // 更新数据库类型配置
  updateDatabaseConfig(dbType, data) {
    return request.put(`/system/database-config/${dbType}`, data)
  },

  // ==================== 存储配置 ====================
  
  // 获取存储配置
  getStorageConfig() {
    return request.get('/system/storage-config')
  },

  // 更新存储配置
  updateStorageConfig(data) {
    return request.put('/system/storage-config', data)
  },

  // 测试存储配置
  testStorageConfig(data) {
    return request.post('/system/storage-config/test', data)
  },

  // ==================== AWS 配置 ====================
  
  // 测试 AWS 连接
  testAwsConnection(data) {
    return request.post('/system/test-aws-connection', data)
  },

  // ==================== 安全配置 ====================
  
  // 获取安全配置
  getSecurityConfig() {
    return request.get('/system/security-config')
  }
}
