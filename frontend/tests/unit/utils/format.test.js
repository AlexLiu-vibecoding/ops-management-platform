/**
 * 格式化工具函数测试
 */
import { describe, it, expect } from 'vitest'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import { formatTime, formatDate, formatRelativeTime } from '@/utils/format'

// 加载 dayjs 插件
dayjs.extend(relativeTime)

describe('formatTime', () => {
  it('应该正确格式化时间', () => {
    const time = '2024-01-15T10:30:00'
    const result = formatTime(time)
    expect(result).toBe('2024-01-15 10:30:00')
  })

  it('应该使用自定义格式', () => {
    const time = '2024-01-15T10:30:00'
    const result = formatTime(time, 'YYYY/MM/DD')
    expect(result).toBe('2024/01/15')
  })

  it('空值应该返回 "-"', () => {
    expect(formatTime(null)).toBe('-')
    expect(formatTime(undefined)).toBe('-')
    expect(formatTime('')).toBe('-')
  })
})

describe('formatDate', () => {
  it('应该正确格式化日期', () => {
    const date = '2024-01-15T10:30:00'
    const result = formatDate(date)
    expect(result).toBe('2024-01-15')
  })

  it('空值应该返回 "-"', () => {
    expect(formatDate(null)).toBe('-')
    expect(formatDate(undefined)).toBe('-')
  })
})

describe('formatRelativeTime', () => {
  it('应该返回相对时间', () => {
    const now = new Date()
    const result = formatRelativeTime(now)
    expect(result).toBe('a few seconds ago')
  })

  it('空值应该返回 "-"', () => {
    expect(formatRelativeTime(null)).toBe('-')
    expect(formatRelativeTime(undefined)).toBe('-')
  })
})
