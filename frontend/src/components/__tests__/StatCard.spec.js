import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '../StatCard.vue'

describe('StatCard', () => {
    it('renders title and value', () => {
        const wrapper = mount(StatCard, {
            props: { title: 'Total Logs', value: 100 }
        })
        expect(wrapper.text()).toContain('Total Logs')
        expect(wrapper.text()).toContain('100')
    })

    it('formats percentage', () => {
        const wrapper = mount(StatCard, {
            props: { title: 'Success Rate', value: 95.5, format: 'percent' }
        })
        expect(wrapper.text()).toContain('95.5%')
    })

    it('formats bytes', () => {
        const wrapper = mount(StatCard, {
            props: { title: 'Size', value: 1024, format: 'bytes' }
        })
        expect(wrapper.text()).toContain('1.0 KB')
    })

    it('applies color class', () => {
        const wrapper = mount(StatCard, {
            props: { title: 'Errors', value: 5, color: 'error' }
        })
        expect(wrapper.classes()).toContain('color-error')
    })
})
