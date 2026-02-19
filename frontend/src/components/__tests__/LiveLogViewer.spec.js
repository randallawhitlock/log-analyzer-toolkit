import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import LiveLogViewer from '../LiveLogViewer.vue'
import { LiveLogService } from '../../services/liveLogs'

const { mockServiceInstance } = vi.hoisted(() => {
    return {
        mockServiceInstance: {
            connect: vi.fn(),
            connectReplay: vi.fn(),
            disconnect: vi.fn(),
            sendCommand: vi.fn(),
            onMessage: vi.fn()
        }
    }
})

// Mock the service
vi.mock('../../services/liveLogs', () => {
    return {
        LiveLogService: vi.fn().mockImplementation(function () { return mockServiceInstance })
    }
})

describe('LiveLogViewer', () => {
    beforeEach(() => {
        vi.clearAllMocks()
    })

    it('renders correctly and initializes connection', () => {
        const wrapper = mount(LiveLogViewer, {
            props: { analysisId: '123' }
        })

        expect(wrapper.find('.viewer-header h3').text()).toBe('Log Viewer')
        expect(mockServiceInstance.onMessage).toHaveBeenCalled()
        expect(mockServiceInstance.connectReplay).toHaveBeenCalledWith('123', null)
    })

    it('can toggle between tail and replay mode', async () => {
        const wrapper = mount(LiveLogViewer, {
            props: { analysisId: '123' }
        })

        const [replayBtn, tailBtn] = wrapper.findAll('.mode-btn')

        // Switch to live tail
        await tailBtn.trigger('click')
        expect(wrapper.vm.mode).toBe('tail')
        expect(mockServiceInstance.disconnect).toHaveBeenCalled()
        expect(mockServiceInstance.connect).toHaveBeenCalledWith('123', null)

        // Switch back to replay
        await replayBtn.trigger('click')
        expect(wrapper.vm.mode).toBe('replay')
        expect(mockServiceInstance.connectReplay).toHaveBeenCalledTimes(2)
    })

    it('handles incoming log messages and level filtering', async () => {
        const wrapper = mount(LiveLogViewer, {
            props: { analysisId: '123' }
        })

        // Simulate incoming log message by retrieving the stored callback
        const messageCallback = mockServiceInstance.onMessage.mock.calls[0][0]

        messageCallback({
            type: 'log',
            payload: { level: 'ERROR', message: 'Something broke', line_num: 0 }
        })

        await wrapper.vm.$nextTick()

        // Should display the error log
        let entries = wrapper.findAll('.log-entry')
        expect(entries.length).toBe(1)
        expect(entries[0].text()).toContain('ERROR')
        expect(entries[0].text()).toContain('Something broke')

        // Toggle off ERROR level
        const errorFilterBtn = wrapper.find('.level-error')
        await errorFilterBtn.trigger('click')

        // Entries should now be hidden
        entries = wrapper.findAll('.log-entry')
        expect(entries.length).toBe(0)
    })

    it('sends commands when playing or changing speed', async () => {
        const wrapper = mount(LiveLogViewer, {
            props: { analysisId: '123' }
        })

        // Click pause
        const playPauseBtn = wrapper.find('.control-btn')
        await playPauseBtn.trigger('click')

        expect(mockServiceInstance.sendCommand).toHaveBeenCalledWith('pause')

        // Change speed
        const speedSelect = wrapper.find('.speed-select')
        await speedSelect.setValue(5)

        expect(mockServiceInstance.sendCommand).toHaveBeenCalledWith('speed', 5)
    })

    it('cleans up on unmount', () => {
        const wrapper = mount(LiveLogViewer, {
            props: { analysisId: '123' }
        })

        wrapper.unmount()
        expect(mockServiceInstance.disconnect).toHaveBeenCalled()
    })
})
