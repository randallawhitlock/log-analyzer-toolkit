import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import AnalysesListView from '../AnalysesListView.vue'

// Mock the composable
const mockGetAnalyses = vi.fn()
vi.mock('../../composables/useApi', async () => {
    const { ref } = await import('vue')
    return {
        useApi: () => ({
            getAnalyses: mockGetAnalyses,
            deleteAnalysis: vi.fn(),
            loading: ref(false),
            error: ref(null)
        })
    }
})

// Mock router link since it's used
const RouterLink = {
    template: '<a><slot></slot></a>',
    props: ['to']
}

describe('AnalysesListView', () => {
    it('renders list of analyses', async () => {
        mockGetAnalyses.mockResolvedValue({
            analyses: [
                { id: '1', filename: 'test.log', detected_format: 'nginx', total_lines: 100, parse_success_rate: 100, error_rate: 0, created_at: '2023-01-01' }
            ]
        })

        const wrapper = mount(AnalysesListView, {
            global: {
                components: {
                    RouterLink
                }
            }
        })

        await flushPromises()

        expect(wrapper.text()).toContain('test.log')
        expect(wrapper.text()).toContain('nginx')
    })

    it('renders empty state when no analyses', async () => {
        mockGetAnalyses.mockResolvedValue({
            analyses: []
        })

        const wrapper = mount(AnalysesListView, {
            global: {
                components: {
                    RouterLink
                }
            }
        })

        await flushPromises()

        expect(wrapper.text()).toContain('No analyses yet')
    })
})
