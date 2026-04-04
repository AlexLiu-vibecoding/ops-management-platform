/**
 * TableActions 组件测试
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { ElButton, ElDropdown, ElDropdownMenu, ElDropdownItem } from 'element-plus'

// Mock Element Plus 组件
const mockTableActions = {
  template: `
    <div class="table-actions">
      <template v-if="shouldShowAll">
        <button 
          v-for="action in visibleActions" 
          :key="action.key"
          :class="[action.danger ? 'danger' : 'primary']"
          @click="$emit(action.event, row)"
        >
          {{ typeof action.label === 'function' ? action.label(row) : action.label }}
        </button>
      </template>
      <template v-else>
        <button 
          v-for="action in primaryActions" 
          :key="action.key"
          class="primary"
          @click="$emit(action.event, row)"
        >
          {{ typeof action.label === 'function' ? action.label(row) : action.label }}
        </button>
        <span v-if="secondaryActions.length > 0" class="more-btn">更多</span>
      </template>
    </div>
  `,
  props: ['row', 'actions', 'maxPrimary', 'showAllThreshold'],
  emits: ['view', 'edit', 'delete'],
  computed: {
    visibleActions() {
      return this.actions.filter(action => {
        if (typeof action.visible === 'function') {
          return action.visible(this.row)
        }
        return action.visible !== false
      })
    },
    shouldShowAll() {
      return this.visibleActions.length <= (this.showAllThreshold || 3)
    },
    primaryActions() {
      const sorted = [...this.visibleActions].sort((a, b) => {
        if (a.primary === true && b.primary !== true) return -1
        if (a.primary !== true && b.primary === true) return 1
        return 0
      })
      return sorted.slice(0, this.maxPrimary || 2)
    },
    secondaryActions() {
      const primaryKeys = this.primaryActions.map(a => a.key)
      return this.visibleActions.filter(a => !primaryKeys.includes(a.key))
    }
  }
}

describe('TableActions', () => {
  const mockRow = { id: 1, name: 'Test' }

  it('应该渲染所有操作按钮（操作数 <= 3）', () => {
    const actions = [
      { key: 'view', label: '查看', event: 'view' },
      { key: 'edit', label: '编辑', event: 'edit' }
    ]
    
    const wrapper = mount(mockTableActions, {
      props: { row: mockRow, actions }
    })
    
    expect(wrapper.findAll('button').length).toBe(2)
    expect(wrapper.text()).toContain('查看')
    expect(wrapper.text()).toContain('编辑')
  })

  it('应该区分主要和次要操作（操作数 > 3）', () => {
    const actions = [
      { key: 'view', label: '查看', event: 'view', primary: true },
      { key: 'edit', label: '编辑', event: 'edit', primary: true },
      { key: 'delete', label: '删除', event: 'delete' },
      { key: 'export', label: '导出', event: 'export' }
    ]
    
    const wrapper = mount(mockTableActions, {
      props: { row: mockRow, actions, maxPrimary: 2 }
    })
    
    const buttons = wrapper.findAll('button')
    expect(buttons.length).toBe(2) // 只显示主要操作
    expect(wrapper.find('.more-btn').exists()).toBe(true)
  })

  it('应该根据 visible 函数过滤操作', () => {
    const actions = [
      { key: 'view', label: '查看', event: 'view', visible: () => true },
      { key: 'edit', label: '编辑', event: 'edit', visible: () => false },
      { key: 'delete', label: '删除', event: 'delete' }
    ]
    
    const wrapper = mount(mockTableActions, {
      props: { row: mockRow, actions }
    })
    
    expect(wrapper.text()).toContain('查看')
    expect(wrapper.text()).not.toContain('编辑')
    expect(wrapper.text()).toContain('删除')
  })

  it('应该正确应用 danger 样式', () => {
    const actions = [
      { key: 'view', label: '查看', event: 'view' },
      { key: 'delete', label: '删除', event: 'delete', danger: true }
    ]
    
    const wrapper = mount(mockTableActions, {
      props: { row: mockRow, actions }
    })
    
    const buttons = wrapper.findAll('button')
    expect(buttons[0].classes()).toContain('primary')
    expect(buttons[1].classes()).toContain('danger')
  })

  it('应该触发对应的事件', async () => {
    const actions = [
      { key: 'view', label: '查看', event: 'view' },
      { key: 'edit', label: '编辑', event: 'edit' }
    ]
    
    const wrapper = mount(mockTableActions, {
      props: { row: mockRow, actions }
    })
    
    await wrapper.findAll('button')[0].trigger('click')
    expect(wrapper.emitted()).toHaveProperty('view')
    expect(wrapper.emitted('view')[0]).toEqual([mockRow])
  })
})
