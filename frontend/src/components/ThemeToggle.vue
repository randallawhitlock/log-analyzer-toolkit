<template>
  <button 
    @click="toggleTheme" 
    class="theme-toggle"
    :title="isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'"
  >
    <span class="theme-icon">{{ isDark ? '☀️' : '🌙' }}</span>
  </button>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'

const isDark = ref(true)

const toggleTheme = () => {
  isDark.value = !isDark.value
}

// Apply theme to document
watch(isDark, (newVal) => {
  document.documentElement.setAttribute('data-theme', newVal ? 'dark' : 'light')
  localStorage.setItem('log-analyzer-theme', newVal ? 'dark' : 'light')
})

// Load saved theme on mount
onMounted(() => {
  const saved = localStorage.getItem('log-analyzer-theme')
  if (saved) {
    isDark.value = saved === 'dark'
  } else {
    // Default to dark or system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    isDark.value = prefersDark
  }
  document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : 'light')
})
</script>

<style scoped>
.theme-toggle {
  background: transparent;
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
  padding: 6px 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.theme-toggle:hover {
  border-color: var(--color-primary, #646cff);
  background: var(--color-bg-tertiary, #2a2a4e);
}

.theme-icon {
  font-size: 18px;
}
</style>
