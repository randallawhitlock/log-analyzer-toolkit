import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import LogUpload from '../LogUpload.vue'
import { useRouter } from 'vue-router'
import { useApi } from '../../composables/useApi'

// Mock dependencies
vi.mock('vue-router', () => ({
    useRouter: vi.fn()
}))

vi.mock('../../composables/useApi', () => ({
    useApi: vi.fn()
}))

describe('LogUpload', () => {
    let mockRouterPush
    let mockAnalyzeLog

    beforeEach(() => {
        mockRouterPush = vi.fn()
        useRouter.mockReturnValue({ push: mockRouterPush })

        mockAnalyzeLog = vi.fn().mockResolvedValue({ id: 'test-123' })
        useApi.mockReturnValue({
            analyzeLog: mockAnalyzeLog,
            loading: false,
            error: null
        })

        vi.useFakeTimers()
    })

    afterEach(() => {
        vi.useRealTimers()
        vi.clearAllMocks()
    })

    it('renders upload prompt correctly', () => {
        const wrapper = mount(LogUpload)
        expect(wrapper.find('.upload-prompt').exists()).toBe(true)
        expect(wrapper.text()).toContain('Choose File')
        expect(wrapper.text()).toContain('log, .txt, .json up to 100 MB')
    })

    it('validates file size and type', async () => {
        const wrapper = mount(LogUpload)

        // Attempt invalid type
        const invalidFile = new File([''], 'test.exe', { type: 'application/x-msdownload' })
        const input = wrapper.find('input[type="file"]')

        // Simulate file input change
        Object.defineProperty(input.element, 'files', {
            value: [invalidFile],
            configurable: true
        })
        await input.trigger('change')

        expect(wrapper.vm.error).toContain('Invalid file type')
        expect(wrapper.find('.error-message').exists()).toBe(true)

        // Attempt oversize file
        const largeFile = new File([''], 'test.log', { type: 'text/plain' })
        Object.defineProperty(largeFile, 'size', { value: 105 * 1024 * 1024 }) // > 100MB
        Object.defineProperty(input.element, 'files', { value: [largeFile], configurable: true })
        await input.trigger('change')

        expect(wrapper.vm.error).toContain('File too large')
    })

    it('handles successful file upload and routes to analysis view', async () => {
        const wrapper = mount(LogUpload)
        const validFile = new File(['dummy content'], 'test.log', { type: 'text/plain' })

        const input = wrapper.find('input[type="file"]')
        Object.defineProperty(input.element, 'files', { value: [validFile], configurable: true })

        // Trigger the upload
        await input.trigger('change')
        await vi.runAllTimersAsync()

        expect(mockAnalyzeLog).toHaveBeenCalledWith(validFile)

        expect(wrapper.emitted('upload-complete')).toBeTruthy()
        expect(wrapper.emitted('upload-complete')[0]).toEqual([{ id: 'test-123' }])

        // Check routing
        expect(mockRouterPush).toHaveBeenCalledWith({ name: 'analysis', params: { id: 'test-123' } })
    })

    it('handles drag and drop events', async () => {
        const wrapper = mount(LogUpload)
        const dropZone = wrapper.find('.drop-zone')

        await dropZone.trigger('dragover')
        expect(wrapper.vm.isDragging).toBe(true)
        expect(dropZone.classes()).toContain('drag-over')

        await dropZone.trigger('dragleave')
        expect(wrapper.vm.isDragging).toBe(false)
        expect(dropZone.classes()).not.toContain('drag-over')
    })
})
