import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LevelChart from '../LevelChart.vue'

describe('LevelChart', () => {
    it('renders correctly with no data', () => {
        const wrapper = mount(LevelChart, {
            props: {
                levelCounts: {}
            }
        })

        expect(wrapper.exists()).toBe(true)
        expect(wrapper.text()).toContain('No severity data available')
        expect(wrapper.findAll('.level-bar').length).toBe(0)
    })

    it('renders correctly with level counts', () => {
        const wrapper = mount(LevelChart, {
            props: {
                levelCounts: {
                    ERROR: 10,
                    INFO: 40,
                    DEBUG: 50
                }
            }
        })

        const bars = wrapper.findAll('.level-bar')
        expect(bars.length).toBe(3)

        // Check order mapping based on config
        const names = wrapper.findAll('.level-name').map(w => w.text())
        expect(names).toEqual(['ERROR', 'INFO', 'DEBUG'])

        // Check percentages
        const percentages = wrapper.findAll('.bar-percentage').map(w => w.text())
        expect(percentages).toEqual(['10.0%', '40.0%', '50.0%'])
    })

    it('allows custom title', () => {
        const wrapper = mount(LevelChart, {
            props: {
                title: 'Custom Severity'
            }
        })

        expect(wrapper.find('.chart-title').text()).toBe('Custom Severity')
    })
})
