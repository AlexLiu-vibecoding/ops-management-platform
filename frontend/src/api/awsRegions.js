/**
 * AWS 区域 API
 */
import request from './index'

/**
 * 获取 AWS 区域列表
 * @param {boolean} enabledOnly - 是否只返回启用的区域
 * @returns {Promise<Array>} 区域列表
 */
export const getAwsRegions = (enabledOnly = true) => {
  return request.get('/aws-regions', {
    params: { enabled_only: enabledOnly }
  })
}

/**
 * 获取按地理区域分组的 AWS 区域列表
 * @param {boolean} enabledOnly - 是否只返回启用的区域
 * @returns {Promise<Array>} 分组的区域列表
 */
export const getAwsRegionsGrouped = (enabledOnly = true) => {
  return request.get('/aws-regions/grouped', {
    params: { enabled_only: enabledOnly }
  })
}
