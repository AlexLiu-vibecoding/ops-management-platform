/**
 * useFormat composable 测试
 */
import { describe, it, expect } from 'vitest'
import { ref, computed } from 'vue'

// 模拟 useFormat composable
function useFormat() {
  const formatBytes = (bytes, decimals = 2) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const dm = decimals < 0 ? 0 : decimals
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i]
  }

  const formatPercent = (value, total) => {
    if (!total) return '0%'
    return ((value / total) * 100).toFixed(2) + '%'
  }

  const formatNumber = (num) => {
    return num?.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',') || '0'
  }

  return {
    formatBytes,
    formatPercent,
    formatNumber
  }
}

describe('useFormat', () => {
  const { formatBytes, formatPercent, formatNumber } = useFormat()

  describe('formatBytes', () => {
    it('应该正确格式化字节', () => {
      expect(formatBytes(0)).toBe('0 B')
      expect(formatBytes(1024)).toBe('1 KB')
      expect(formatBytes(1024 * 1024)).toBe('1 MB')
      expect(formatBytes(1024 * 1024 * 1024)).toBe('1 GB')
    })

    it('应该支持自定义小数位数', () => {
      expect(formatBytes(1536, 0)).toBe('2 KB')
      expect(formatBytes(1536, 2)).toBe('1.5 KB')
    })
  })

  describe('formatPercent', () => {
    it('应该正确计算百分比', () => {
      expect(formatPercent(50, 100)).toBe('50.00%')
      expect(formatPercent(1, 3)).toBe('33.33%')
    })

    it('应该处理除数为 0 的情况', () => {
      expect(formatPercent(50, 0)).toBe('0%')
      expect(formatPercent(50, null)).toBe('0%')
    })
  })

  describe('formatNumber', () => {
    it('应该添加千分位分隔符', () => {
      expect(formatNumber(1000)).toBe('1,000')
      expect(formatNumber(1000000)).toBe('1,000,000')
      expect(formatNumber(123456789)).toBe('123,456,789')
    })

    it('应该处理空值', () => {
      expect(formatNumber(null)).toBe('0')
      expect(formatNumber(undefined)).toBe('0')
    })
  })
})
