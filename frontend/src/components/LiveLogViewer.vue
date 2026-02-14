<template>
  <div class="live-log-viewer">
    <div class="viewer-header">
      <div class="header-left">
        <h3>🔴 Live Tail</h3>
        <span class="status-badge" :class="status">
          {{ status === 'connected' ? 'Live' : 'Disconnected' }}
        </span>
      </div>
      <div class="header-controls">
        <div class="filter-input-wrapper">
          <span class="filter-icon">🔍</span>
          <input
            v-model="filterInput"
            @keyup.enter="applyFilter"
            placeholder="Regex filter..."
            class="filter-input"
          />
        </div>
        <label class="autoscroll-toggle">
          <input type="checkbox" v-model="autoScroll" />
          <span>Auto-scroll</span>
        </label>
        <button @click="clearLogs" class="clear-btn" title="Clear logs">🚫</button>
      </div>
    </div>

    <div ref="logContainer" class="log-container">
      <div v-if="logs.length === 0" class="empty-state">
        Waiting for logs...
      </div>
      <div v-for="(log, index) in logs" :key="index" class="log-entry">
        <span class="timestamp">{{ formatTime(log.timestamp) }}</span>
        <span class="message">{{ log.line }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { LiveLogService } from '../services/liveLogs'

const props = defineProps({
  filePath: {
    type: String,
    required: true
  }
})

const status = ref('disconnected')
const logs = ref([])
const filterInput = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)
const service = new LiveLogService(import.meta.env.VITE_API_URL || 'http://localhost:8000')

const connect = () => {
  service.connect(props.filePath, filterInput.value)
}

const applyFilter = () => {
  connect() // Reconnect with new filter
}

const clearLogs = () => {
  logs.value = []
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  return new Date(isoString).toLocaleTimeString()
}

const scrollToBottom = () => {
  if (autoScroll.value && logContainer.value) {
    nextTick(() => {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    })
  }
}

onMounted(() => {
  service.onMessage((event) => {
    if (event.type === 'status') {
      status.value = event.payload
    } else if (event.type === 'log') {
      logs.value.push(event.payload)
      // Keep only last 1000 lines to prevent memory issues
      if (logs.value.length > 1000) {
        logs.value.shift()
      }
      scrollToBottom()
    } else if (event.type === 'error') {
      console.error('Live Log Error:', event.payload)
    }
  })

  connect()
})

onUnmounted(() => {
  service.disconnect()
})

// Watch for file path changes
watch(() => props.filePath, () => {
  logs.value = []
  connect()
})
</script>

<style scoped>
.live-log-viewer {
  background: #1e1e1e; /* Darker background for terminal look */
  border: 1px solid #333;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  height: 500px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #252526;
  border-bottom: 1px solid #333;
  border-radius: 8px 8px 0 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h3 {
  margin: 0;
  font-size: 14px;
  color: #fff;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 10px;
  background: #333;
  color: #888;
  text-transform: uppercase;
  font-weight: bold;
}

.status-badge.connected {
  background: #4caf5020;
  color: #4caf50;
  border: 1px solid #4caf5040;
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-icon {
  position: absolute;
  left: 8px;
  font-size: 12px;
  color: #666;
}

.filter-input {
  background: #333;
  border: 1px solid #444;
  color: #fff;
  padding: 4px 8px 4px 24px;
  border-radius: 4px;
  font-size: 12px;
  width: 150px;
  transition: width 0.2s;
}

.filter-input:focus {
  width: 200px;
  outline: none;
  border-color: #646cff;
}

.autoscroll-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #aaa;
  cursor: pointer;
  user-select: none;
}

.clear-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.clear-btn:hover {
  background: #333;
}

.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  color: #d4d4d4;
  font-size: 12px;
  line-height: 1.5;
}

.empty-state {
  color: #666;
  text-align: center;
  margin-top: 40px;
  font-style: italic;
}

.log-entry {
  display: flex;
  gap: 12px;
  padding: 1px 0;
}

.log-entry:hover {
  background: #ffffff05;
}

.timestamp {
  color: #569cd6;
  flex-shrink: 0;
  user-select: none;
}

.message {
  white-space: pre-wrap;
  word-break: break-all;
}

/* Scrollbar styling */
.log-container::-webkit-scrollbar {
  width: 10px;
}

.log-container::-webkit-scrollbar-track {
  background: #1e1e1e;
}

.log-container::-webkit-scrollbar-thumb {
  background: #444;
  border-radius: 5px;
  border: 2px solid #1e1e1e;
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: #555;
}
</style>
