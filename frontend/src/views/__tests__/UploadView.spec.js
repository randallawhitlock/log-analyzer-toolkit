import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import UploadView from '../UploadView.vue'
import { useApi } from '../../composables/useApi'

vi.mock('../../composables/useApi', () => ({
    useApi: vi.fn()
}))

const RouterLinkStub = {
    template: '<a :href="to"><slot /></a>',
    props: ['to']
}

vi.mock('../../components/LogUpload.vue', () => ({
    default: {
        name: 'LogUpload',
        template: '<div class="log-upload-mock"></div>'
    }
}))

describe('UploadView', () => {
    let mockGetFormats

    beforeEach(() => {
        mockGetFormats = vi.fn().mockResolvedValue({
            formats: [
                { name: 'Nginx', description: 'Nginx access log format. Parses standard lines.' }
            ]
        })

        useApi.mockReturnValue({
            getFormats: mockGetFormats
        })
    })

    it('renders header, upload component, and supported formats', async () => {
        const wrapper = mount(UploadView, {
            global: {
                stubs: {
                    RouterLink: RouterLinkStub,
                    LogUpload: true
                }
            }
        })

        // Assert API is called
        expect(mockGetFormats).toHaveBeenCalled()

        // Header exists
        expect(wrapper.find('.page-header h1').text()).toBe('Upload Log File')

        // Formats load
        await wrapper.vm.$nextTick()
        await wrapper.vm.$nextTick()

        const formatCards = wrapper.findAll('.format-card')
        expect(formatCards.length).toBe(1)
        expect(formatCards[0].text()).toContain('Nginx')
        expect(formatCards[0].text()).toContain('Nginx access log format')
    })
})
