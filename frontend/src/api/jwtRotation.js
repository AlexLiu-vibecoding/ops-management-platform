/**
 * JWT 轮换 API
 */
import request from './index'

/**
 * 获取 JWT 轮换状态
 */
export function getJwtRotationStatus() {
  return request.get('/jwt-rotation/status')
}

/**
 * 获取所有 JWT 密钥版本
 */
export function getJwtVersions() {
  return request.get('/jwt-rotation/versions')
}

/**
 * 生成新的 JWT 密钥
 */
export function generateJwtKey(keyId = null) {
  return request.post('/jwt-rotation/generate-key', { key_id: keyId })
}

/**
 * 切换 JWT 密钥版本
 */
export function switchJwtVersion(targetVersion) {
  return request.post('/jwt-rotation/switch-version', { target_version: targetVersion })
}

/**
 * JWT 一键轮换
 */
export function fullJwtRotation() {
  return request.post('/jwt-rotation/full-rotation')
}

/**
 * 删除 JWT 密钥版本
 */
export function deleteJwtKey(keyId) {
  return request.delete(`/jwt-rotation/keys/${keyId}`)
}
