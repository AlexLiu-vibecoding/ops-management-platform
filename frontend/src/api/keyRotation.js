/**
 * 密钥轮换 API
 */
import request from './index'

/**
 * 获取密钥轮换状态
 */
export function getKeyRotationStatus() {
  return request.get('/key-rotation/status')
}

/**
 * 获取密钥版本信息
 */
export function getKeyVersions() {
  return request.get('/key-rotation/versions')
}

/**
 * 获取加密数据统计
 */
export function getEncryptionStatistics() {
  return request.get('/key-rotation/statistics')
}

/**
 * 获取轮换配置
 */
export function getRotationConfig() {
  return request.get('/key-rotation/config')
}

/**
 * 更新轮换配置
 * @param {Object} config - 配置对象
 */
export function updateRotationConfig(config) {
  return request.put('/key-rotation/config', config)
}

/**
 * 预览迁移
 */
export function getMigrationPreview() {
  return request.get('/key-rotation/migration-preview')
}

/**
 * 执行迁移
 * @param {number} batchSize - 批次大小
 */
export function executeMigration(batchSize = 100) {
  return request.post(`/key-rotation/migrate?batch_size=${batchSize}`)
}

/**
 * 切换密钥版本
 * @param {string} targetVersion - 目标版本 (v1 或 v2)
 */
export function switchKeyVersion(targetVersion) {
  return request.post('/key-rotation/switch-version', { target_version: targetVersion })
}

/**
 * 获取轮换历史
 * @param {number} page - 页码
 * @param {number} pageSize - 每页大小
 */
export function getRotationHistory(page = 1, pageSize = 20) {
  return request.get('/key-rotation/history', { params: { page, page_size: pageSize } })
}

/**
 * 触发自动轮换（手动触发）
 */
export function triggerAutoRotation() {
  return request.post('/key-rotation/auto-rotate')
}

/**
 * 生成新的 V2 密钥
 */
export function generateV2Key() {
  return request.post('/key-rotation/generate-v2-key')
}
