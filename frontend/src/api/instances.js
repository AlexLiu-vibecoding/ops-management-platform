import request from './index'

/**
 * 实例管理 API
 * 
 * 注意：后端已拆分为两个 API：
 * - /rdb-instances - MySQL/PostgreSQL 实例
 * - /redis-instances - Redis 实例
 * 
 * 此文件提供统一接口，保持向后兼容
 */

// RDB 实例 API
const rdbInstancesApi = {
  getList(params) {
    return request.get('/rdb-instances', { params })
  },

  getDetail(id) {
    return request.get(`/rdb-instances/${id}`)
  },

  create(data) {
    return request.post('/rdb-instances', data)
  },

  update(id, data) {
    return request.put(`/rdb-instances/${id}`, data)
  },

  delete(id) {
    return request.delete(`/rdb-instances/${id}`)
  },

  testConnection(data) {
    return request.post('/rdb-instances/test', data)
  },

  checkStatus(id) {
    return request.post(`/rdb-instances/${id}/check`)
  },

  getVariables(id) {
    return request.get(`/rdb-instances/${id}/variables`)
  },

  getDatabases(id) {
    return request.get(`/rdb-instances/${id}/databases`)
  },

  getTables(id, database) {
    return request.get(`/rdb-instances/${id}/databases/${database}/tables`)
  }
}

// Redis 实例 API
const redisInstancesApi = {
  getList(params) {
    return request.get('/redis-instances', { params })
  },

  getDetail(id) {
    return request.get(`/redis-instances/${id}`)
  },

  create(data) {
    return request.post('/redis-instances', data)
  },

  update(id, data) {
    return request.put(`/redis-instances/${id}`, data)
  },

  delete(id) {
    return request.delete(`/redis-instances/${id}`)
  },

  testConnection(data) {
    return request.post('/redis-instances/test', data)
  },

  checkStatus(id) {
    return request.post(`/redis-instances/${id}/check`)
  },

  getSlowLogs(id, params) {
    return request.get(`/redis-instances/${id}/slow-logs`, { params })
  },

  getMemoryStats(id) {
    return request.get(`/redis-instances/${id}/memory-stats`)
  },

  getInfo(id) {
    return request.get(`/redis-instances/${id}/info`)
  }
}

// 统一实例 API（向后兼容）
export const instancesApi = {
  /**
   * 获取实例列表
   * @param {Object} params - 查询参数
   * @param {string} params.db_type - 实例类型: 'mysql', 'postgresql', 'redis', 或不传获取全部
   */
  async getList(params = {}) {
    const { db_type, ...restParams } = params
    
    // 如果指定了 db_type，只获取对应类型
    if (db_type === 'redis') {
      const res = await redisInstancesApi.getList(restParams)
      return {
        total: res.total,
        items: res.items.map(item => ({ ...item, db_type: 'redis' }))
      }
    }
    
    if (db_type === 'mysql' || db_type === 'postgresql') {
      const res = await rdbInstancesApi.getList({ ...restParams, db_type })
      return {
        total: res.total,
        items: res.items.map(item => ({ 
          ...item, 
          db_type: item.db_type?.value || item.db_type?.toLowerCase() || db_type 
        }))
      }
    }
    
    // 获取所有实例
    const [rdbRes, redisRes] = await Promise.all([
      rdbInstancesApi.getList(restParams).catch(() => ({ total: 0, items: [] })),
      redisInstancesApi.getList(restParams).catch(() => ({ total: 0, items: [] }))
    ])
    
    const rdbItems = (rdbRes.items || []).map(item => ({
      ...item,
      db_type: item.db_type?.value || item.db_type?.toLowerCase() || 'mysql'
    }))
    
    const redisItems = (redisRes.items || []).map(item => ({
      ...item,
      db_type: 'redis'
    }))
    
    // 合并并按创建时间排序
    const allItems = [...rdbItems, ...redisItems].sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
      return timeB - timeA
    })
    
    return {
      total: allItems.length,
      items: allItems
    }
  },

  /**
   * 获取实例详情
   * @param {number} id - 实例 ID
   * @param {string} dbType - 实例类型 (可选，不传会自动判断)
   */
  async getDetail(id, dbType = null) {
    // 如果指定了类型，直接调用对应 API
    if (dbType === 'redis') {
      const res = await redisInstancesApi.getDetail(id)
      return { ...res, db_type: 'redis' }
    }
    if (dbType === 'mysql' || dbType === 'postgresql') {
      const res = await rdbInstancesApi.getDetail(id)
      return { ...res, db_type: res.db_type?.value || res.db_type?.toLowerCase() || dbType }
    }
    
    // 否则尝试从两个 API 获取
    try {
      const res = await rdbInstancesApi.getDetail(id)
      return { ...res, db_type: res.db_type?.value || res.db_type?.toLowerCase() || 'mysql' }
    } catch (e) {
      // 如果 RDB 找不到，尝试 Redis
      try {
        const res = await redisInstancesApi.getDetail(id)
        return { ...res, db_type: 'redis' }
      } catch (e2) {
        throw new Error('实例不存在')
      }
    }
  },

  /**
   * 创建实例
   * @param {Object} data - 实例数据，必须包含 db_type 字段
   */
  create(data) {
    if (data.db_type === 'redis') {
      return redisInstancesApi.create(data)
    }
    return rdbInstancesApi.create(data)
  },

  /**
   * 更新实例
   * @param {number} id - 实例 ID
   * @param {Object} data - 更新数据
   */
  update(id, data) {
    if (data.db_type === 'redis') {
      return redisInstancesApi.update(id, data)
    }
    return rdbInstancesApi.update(id, data)
  },

  /**
   * 删除实例
   * @param {number} id - 实例 ID
   * @param {string} dbType - 实例类型
   */
  delete(id, dbType) {
    if (dbType === 'redis') {
      return redisInstancesApi.delete(id)
    }
    return rdbInstancesApi.delete(id)
  },

  /**
   * 测试连接
   * @param {Object} data - 连接数据，必须包含 db_type 字段
   */
  testConnection(data) {
    if (data.db_type === 'redis') {
      return redisInstancesApi.testConnection(data)
    }
    return rdbInstancesApi.testConnection(data)
  },

  /**
   * 检查状态
   * @param {number} id - 实例 ID
   * @param {string} dbType - 实例类型
   */
  checkStatus(id, dbType) {
    if (dbType === 'redis') {
      return redisInstancesApi.checkStatus(id)
    }
    return rdbInstancesApi.checkStatus(id)
  },

  /**
   * 获取实例变量 (仅 RDB)
   */
  getVariables(id) {
    return rdbInstancesApi.getVariables(id)
  },

  /**
   * 获取数据库列表 (仅 RDB)
   */
  getDatabases(id) {
    return rdbInstancesApi.getDatabases(id)
  },

  /**
   * 获取表列表 (仅 RDB)
   */
  getTables(id, database) {
    return rdbInstancesApi.getTables(id, database)
  },

  /**
   * 获取分组列表
   */
  getGroups() {
    return request.get('/rdb-instances/groups/')
  },

  /**
   * 创建分组
   */
  createGroup(data) {
    return request.post('/rdb-instances/groups/', null, { params: data })
  },

  /**
   * 获取 Redis 慢日志
   */
  getRedisSlowLogs(id, params) {
    return redisInstancesApi.getSlowLogs(id, params)
  },

  /**
   * 获取 Redis 内存统计
   */
  getRedisMemoryStats(id) {
    return redisInstancesApi.getMemoryStats(id)
  },

  /**
   * 获取 Redis INFO
   */
  getRedisInfo(id) {
    return redisInstancesApi.getInfo(id)
  }
}

// 导出单独的 API 供特定场景使用
export { rdbInstancesApi, redisInstancesApi }
