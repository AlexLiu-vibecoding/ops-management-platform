/**
 * AWS 区域常量和辅助函数
 * 数据从后端 API 获取，确保各页面数据源一致
 */

/**
 * AWS 区域项接口
 */
export interface AWSRegionItem {
  id: number
  region_code: string
  region_name: string
  geo_group: string
  display_order: number
  is_enabled: boolean
}

/**
 * AWS 区域分组接口
 */
export interface AWSRegionGrouped {
  geo_group: string
  regions: AWSRegionItem[]
}

/**
 * 根据区域代码获取区域名称（用于显示）
 * 如果没有找到，返回原始区域代码
 */
export const getAwsRegionName = (regionCode: string, regions: AWSRegionItem[]): string => {
  if (!regionCode) return ''
  const region = regions.find(r => r.region_code === regionCode)
  return region?.region_name || regionCode
}

/**
 * 检测是否为 RDS endpoint
 * @param host 主机地址
 * @returns 是否为 RDS endpoint
 */
export const isRdsEndpoint = (host: string | null | undefined): boolean => {
  if (!host) return false
  const patterns = [
    /\.rds\.amazonaws\.com$/i,
    /\.rds\.amazonaws\.com\.cn$/i,
  ]
  return patterns.some(pattern => pattern.test(host))
}

/**
 * 从 RDS endpoint 解析 AWS 区域代码
 * 注意：此函数只返回区域代码，需要配合 regions 数据获取区域名称
 * @param host 主机地址
 * @returns 区域代码或 null
 */
export const parseAwsRegion = (host: string | null | undefined): string | null => {
  if (!host) return null
  
  // 匹配 RDS endpoint 格式: xxx.region.rds.amazonaws.com
  const match = host.match(/\.([a-z0-9-]+)\.rds\.amazonaws\.com/i)
  if (match) {
    return match[1]
  }
  
  // 中国区 RDS endpoint 格式: xxx.region.rds.amazonaws.com.cn
  const cnMatch = host.match(/\.([a-z0-9-]+)\.rds\.amazonaws\.com\.cn/i)
  if (cnMatch) {
    return cnMatch[1]
  }
  
  // 宽松匹配：提取任何看起来像 AWS 区域的部分
  const loosePattern = /([a-z]{2}-[a-z]+-\d+)/gi
  const matches = host.match(loosePattern)
  if (matches && matches.length > 0) {
    return matches[0].toLowerCase()
  }
  
  return null
}
