/**
 * 格式化工具函数
 */
import dayjs from 'dayjs'

/**
 * 格式化时间
 * @param {string|Date} time - 时间
 * @param {string} format - 格式，默认 'YYYY-MM-DD HH:mm:ss'
 * @returns {string} 格式化后的时间字符串
 */
export const formatTime = (time, format = 'YYYY-MM-DD HH:mm:ss') => {
  if (!time) return '-'
  return dayjs(time).format(format)
}

/**
 * 格式化日期
 * @param {string|Date} date - 日期
 * @param {string} format - 格式，默认 'YYYY-MM-DD'
 * @returns {string} 格式化后的日期字符串
 */
export const formatDate = (date, format = 'YYYY-MM-DD') => {
  if (!date) return '-'
  return dayjs(date).format(format)
}

/**
 * 相对时间
 * @param {string|Date} time - 时间
 * @returns {string} 相对时间描述
 */
export const formatRelativeTime = (time) => {
  if (!time) return '-'
  return dayjs(time).fromNow()
}
