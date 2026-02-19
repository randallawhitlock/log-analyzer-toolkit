import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import HomeView from '../HomeView.vue'
import { useApi } from '../../composables/useApi'

// Mock dependencies
vi.mock('../../composables/useApi', () => ({
    useApi: vi.fn()
}))

// Mock components
vi.mock('../../components/LogUpload.vue', () => ({
    default: {
        name: 'LogUpload',
        template: '<div class="log-upload-mock"></div>'
    }
}))

// Mock router-link
const RouterLinkStub = {
    template: '<a :href="to"><slot /></a>',
    props: ['to']
}

describe('HomeView', () => {
    let mockGetAnalyses

    beforeEach(() => {
        mockGetAnalyses = vi.fn().mockResolvedValue({
            analyses: [
                {
                    id: '1',
                    filename: 'test.log',
                    detected_format: 'nginx',
                    parse_success_rate: 95.5,
                    total_lines: 1000,
                    created_at: new Date().toISOString()
                }
            ]
        })

        useApi.mockReturnValue({
            getAnalyses: mockGetAnalyses
        })
    })

    it('renders hero section and calls getAnalyses on mount', async () => {
        const wrapper = mount(HomeView, {
            global: {
                stubs: {
                    RouterLink: RouterLinkStub,
                    LogUpload: true
                }
            }
        })

        // Check header
        expect(wrapper.find('.hero-title').text()).toContain('Log Analyzer')

        // Evaluate API call
        expect(mockGetAnalyses).toHaveBeenCalledWith({ limit: 3 })

        // Await promise resolution
        await wrapper.vm.$nextTick()
        await wrapper.vm.$nextTick() // Await data loading

        // Check recent analyses section
        expect(wrapper.find('.recent-section').exists()).toBe(true)
        expect(wrapper.find('.card-title').text()).toBe('test.log')
    })

    it('renders feature cards', () => {
        const wrapper = mount(HomeView, {
            global: {
                stubs: {
                    RouterLink: RouterLinkStub,
                    LogUpload: true
                }
            }
        })

        const featureCards = wrapper.findAll('.feature-card')
        expect(featureCards.length).toBe(3)
        expect(featureCards[0].text()).toContain('Auto-Detection')
        expect(featureCards[1].text()).toContain('Deep Analysis')
        expect(featureCards[2].text()).toContain('AI-Powered Triage')
    })
})
