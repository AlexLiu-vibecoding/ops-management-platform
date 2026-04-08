/**
 * 密钥轮换 API - 支持动态多版本
 */
import request from './index'

/**
 * 获取密钥轮换状态
 */
export function getKeyRotationStatus() {
  return request.get('/key-rotation/status')
}

/**
 * 获取所有密钥版本
 */
export function getKeyVersions() {
  return request.get('/key-rotation/versions')
}

/**
 * 获取轮换配置
 */
export function getRotationConfig() {
  return request.get('/key-rotation/config')
}

/**
 * 更新轮换配置
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
 */
export function executeMigration(batchSize = 100) {
  return request.post(`/key-rotation/migrate?batch_size=${batchSize}`)
}

/**
 * 切换密钥版本
 */
export function switchKeyVersion(targetVersion) {
  console.log('API 调用: switchKeyVersion', targetVersion)
  return request.post('/key-rotation/switch-version', { target_version })
    .then(res => {
      console.log('API 返回数据:', res)
      return res
    })
    .catch(err => {
      console.error('API 错误:', err)
      throw err
    })
}

/**
 * 生成新的密钥版本
 */
export function generateNewKey() {
  return request.post('/key-rotation/generate-key')
}

/**
 * 获取轮换历史
 */
export function getRotationHistory(page = 1, pageSize = 20) {
  return request.get('/key-rotation/history', { params: { page, page_size: pageSize } })
}

/**
 * 一键轮换
 */
export function fullRotation() {
  return request.post('/key-rotation/full-rotation')
}

/**
 * 触发自动轮换
 */
export function triggerAutoRotation() {
  return request.post('/key-rotation/auto-rotate')
}
