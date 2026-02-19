import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'
import ThemeToggle from '../ThemeToggle.vue'

describe('ThemeToggle', () => {
    beforeEach(() => {
        // Clear localStorage
        localStorage.clear()

        // Mock matchMedia
        Object.defineProperty(window, 'matchMedia', {
            writable: true,
            value: vi.fn().mockImplementation(query => ({
                matches: false,
                media: query,
                onchange: null,
                addListener: vi.fn(),
                removeListener: vi.fn(),
                addEventListener: vi.fn(),
                removeEventListener: vi.fn(),
                dispatchEvent: vi.fn(),
            })),
        })
    })

    afterEach(() => {
        vi.restoreAllMocks()
    })

    it('renders correctly', () => {
        const wrapper = mount(ThemeToggle)
        expect(wrapper.exists()).toBe(true)
    })

    it('defaults to light mode when no localStorage or media preference is set', () => {
        const wrapper = mount(ThemeToggle)
        // Based on matchMedia returning false, isDark should be false initially
        expect(wrapper.vm.isDark).toBe(false)
        expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('respects saved localStorage preference', () => {
        localStorage.setItem('log-analyzer-theme', 'dark')
        const wrapper = mount(ThemeToggle)
        expect(wrapper.vm.isDark).toBe(true)
        expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('toggles theme when button is clicked', async () => {
        const wrapper = mount(ThemeToggle)

        // Initial state: light
        expect(wrapper.vm.isDark).toBe(false)

        // Click toggle
        await wrapper.find('button').trigger('click')
        await flushPromises()
        await nextTick()

        // New state: dark
        expect(wrapper.vm.isDark).toBe(true)
        expect(localStorage.getItem('log-analyzer-theme')).toBe('dark')
    })
})
