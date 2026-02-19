import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AnalysisView from '../AnalysisView.vue'
import { useRoute, useRouter } from 'vue-router'
import { useApi } from '../../composables/useApi'

// Mock dependencies
vi.mock('vue-router', () => ({
    useRoute: vi.fn(),
    useRouter: vi.fn()
}))

vi.mock('../../composables/useApi', () => ({
    useApi: vi.fn()
}))

// Mock Chart.js completely avoiding canvas contexts
vi.mock('chart.js/auto', () => ({
    default: vi.fn().mockImplementation(() => ({
        destroy: vi.fn()
    }))
}))

// Mock child components
const StatCardStub = { template: '<div class="stat-card"></div>', props: ['title', 'value'] }
const LevelChartStub = { template: '<div class="level-chart"></div>', props: ['levelCounts'] }
const LiveLogViewerStub = { template: '<div class="live-log-viewer"></div>', props: ['analysisId'] }
const RouterLinkStub = { template: '<a :href="to"><slot /></a>', props: ['to'] }

describe('AnalysisView', () => {
    let mockRoute
    let mockRouterPush
    let mockGetAnalysis
    let mockDeleteAnalysis
    let mockGetTriagesForAnalysis

    beforeEach(() => {
        mockRoute = { params: { id: 'test-123' } }
        useRoute.mockReturnValue(mockRoute)

        mockRouterPush = vi.fn()
        useRouter.mockReturnValue({ push: mockRouterPush })

        mockGetAnalysis = vi.fn().mockResolvedValue({
            id: 'test-123',
            filename: 'error.log',
            detected_format: 'json',
            total_lines: 1000,
            parse_success_rate: 99.0,
            level_counts: { ERROR: 10, INFO: 990 }
        })

        mockDeleteAnalysis = vi.fn().mockResolvedValue(true)

        mockGetTriagesForAnalysis = vi.fn().mockResolvedValue([
            {
                id: 't1',
                overall_severity: 'HIGH',
                confidence: 0.95,
                provider_used: 'claude',
                summary: 'Root cause found'
            }
        ])

        useApi.mockReturnValue({
            getAnalysis: mockGetAnalysis,
            deleteAnalysis: mockDeleteAnalysis,
            getTriagesForAnalysis: mockGetTriagesForAnalysis,
            runTriage: vi.fn(),
            deepDiveIssue: vi.fn(),
            getLogPreview: vi.fn(),
            loading: false,
            error: null
        })

        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
        vi.clearAllMocks()
    })

    it('renders correctly and loads data', async () => {
        const wrapper = mount(AnalysisView, {
            global: {
                stubs: {
                    StatCard: StatCardStub,
                    LevelChart: LevelChartStub,
                    LiveLogViewer: LiveLogViewerStub,
                    RouterLink: RouterLinkStub
                }
            }
        })

        expect(mockGetAnalysis).toHaveBeenCalledWith('test-123')

        await flushPromises()

        expect(wrapper.find('h1').text()).toContain('error.log')
        expect(wrapper.find('.format-badge').text()).toBe('json')
        expect(wrapper.find('.triage-section').exists()).toBe(true)
    })

    it('displays delete confirmation modal and executes delete', async () => {
        const wrapper = mount(AnalysisView, {
            global: { stubs: { StatCard: true, LevelChart: true, LiveLogViewer: true, RouterLink: true } }
        })

        await wrapper.vm.$nextTick()
        await wrapper.vm.$nextTick()

        // Assert modal hidden
        expect(wrapper.find('.modal-overlay').exists()).toBe(false)

        // Click delete header action button
        const deleteBtn = wrapper.find('.delete-btn')
        await deleteBtn.trigger('click')

        // Check that modal appears
        expect(wrapper.vm.showDeleteModal).toBe(true)
        const modal = wrapper.find('.modal-overlay')
        expect(modal.exists()).toBe(true)
        expect(modal.text()).toContain('Confirm Deletion')

        // Execute delete
        await modal.find('.confirm-btn').trigger('click')
        await wrapper.vm.$nextTick()

        expect(mockDeleteAnalysis).toHaveBeenCalledWith('test-123')
        expect(mockRouterPush).toHaveBeenCalledWith('/')
    })

    it('polls if analysis is pending', async () => {
        // Override default mock to simulate pending
        const pendingAnalysis = { id: 'test-123', detected_format: 'pending' }
        const completeAnalysis = { id: 'test-123', detected_format: 'csv' }

        mockGetAnalysis
            .mockResolvedValueOnce(pendingAnalysis)
            .mockResolvedValueOnce(completeAnalysis)

        const wrapper = mount(AnalysisView, {
            global: { stubs: { StatCard: true, LevelChart: true, LiveLogViewer: true, RouterLink: true } }
        })

        await wrapper.vm.$nextTick()
        expect(wrapper.vm.analysis.detected_format).toBe('pending')

        // Advance internal polling timer by 2.1s
        await vi.advanceTimersByTimeAsync(2100)

        // Wait for the asynchronous poll fetch to resolve
        await wrapper.vm.$nextTick()
        await wrapper.vm.$nextTick()

        expect(mockGetAnalysis).toHaveBeenCalledTimes(2)
        expect(wrapper.vm.analysis.detected_format).toBe('csv')
    })
})
