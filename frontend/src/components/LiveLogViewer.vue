<template>
  <div class="live-log-viewer">
    <!-- Header -->
    <div class="viewer-header">
      <div class="header-left">
        <h3>Log Viewer</h3>
        <span class="status-badge" :class="statusClass">{{ statusLabel }}</span>
        <span v-if="totalLines > 0" class="line-counter">
          {{ currentLineNum.toLocaleString() }} / {{ totalLines.toLocaleString() }} lines
        </span>
      </div>
      <div class="header-controls">
        <!-- Mode toggle -->
        <div class="mode-toggle">
          <button
            @click="setMode('replay')"
            class="mode-btn"
            :class="{ active: mode === 'replay' }"
            title="Replay: stream log at configurable speed"
          >Replay</button>
          <button
            @click="setMode('tail')"
            class="mode-btn"
            :class="{ active: mode === 'tail' }"
            title="Tail: watch for new lines appended to file"
          >Live Tail</button>
        </div>

        <!-- Replay controls -->
        <template v-if="mode === 'replay'">
          <button @click="togglePlay" class="control-btn" :title="playing ? 'Pause' : 'Play'">
            {{ playing ? '| |' : '>' }}
          </button>
          <select v-model.number="speed" @change="changeSpeed" class="speed-select" title="Playback speed">
            <option :value="1">1x</option>
            <option :value="2">2x</option>
            <option :value="5">5x</option>
            <option :value="10">10x</option>
            <option :value="0">Max</option>
          </select>
        </template>

        <!-- Filter -->
        <div class="filter-input-wrapper">
          <input
            v-model="filterInput"
            @keyup.enter="reconnect"
            placeholder="Regex filter..."
            class="filter-input"
          />
        </div>

        <!-- Level filters -->
        <div class="level-filters">
          <button
            v-for="lvl in allLevels"
            :key="lvl"
            @click="toggleLevel(lvl)"
            class="level-btn"
            :class="[`level-${lvl.toLowerCase()}`, { inactive: !activeLevels.has(lvl) }]"
            :title="`Toggle ${lvl} lines`"
          >{{ lvl }}</button>
        </div>

        <!-- Utility -->
        <label class="autoscroll-toggle">
          <input type="checkbox" v-model="autoScroll" />
          <span>Auto-scroll</span>
        </label>
        <button @click="clearLogs" class="control-btn" title="Clear display">Clear</button>
      </div>
    </div>

    <!-- Progress bar (replay mode) -->
    <div v-if="mode === 'replay' && totalLines > 0" class="progress-bar">
      <div class="progress-fill" :style="{ width: (progress * 100) + '%' }"></div>
    </div>

    <!-- Log output -->
    <div ref="logContainer" class="log-container">
      <div v-if="filteredLogs.length === 0" class="empty-state">
        {{ status === 'connected' ? 'Waiting for logs...' : 'Click Play or switch to Live Tail to start' }}
      </div>
      <div
        v-for="(log, index) in filteredLogs"
        :key="index"
        class="log-entry"
        :class="`entry-${(log.level || 'INFO').toLowerCase()}`"
      >
        <span v-if="log.line_num !== undefined" class="line-num">{{ log.line_num + 1 }}</span>
        <span v-if="log.level" class="level-badge" :class="`badge-${log.level.toLowerCase()}`">{{ log.level }}</span>
        <span v-if="log.timestamp" class="timestamp">{{ formatTime(log.timestamp) }}</span>
        <span v-if="log.source" class="source">{{ log.source }}</span>
        <span class="message">{{ log.message || log.line }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { LiveLogService } from '../services/liveLogs'

const props = defineProps({
  analysisId: {
    type: String,
    required: true
  }
})

// State
const mode = ref('replay') // 'replay' | 'tail'
const status = ref('disconnected')
const playing = ref(true)
const speed = ref(1)
const logs = ref([])
const filterInput = ref('')
const autoScroll = ref(true)
const logContainer = ref(null)
const totalLines = ref(0)
const currentLineNum = ref(0)
const progress = ref(0)

// Level filtering
const allLevels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
const activeLevels = ref(new Set(allLevels))

const service = new LiveLogService(import.meta.env.VITE_API_URL || 'http://localhost:8000')

// Computed
const statusClass = computed(() => {
  if (status.value === 'connected' && mode.value === 'replay' && !playing.value) return 'paused'
  return status.value
})

const statusLabel = computed(() => {
  if (status.value === 'connected') {
    if (mode.value === 'replay') return playing.value ? 'Replaying' : 'Paused'
    return 'Live'
  }
  if (status.value === 'complete') return 'Complete'
  return 'Disconnected'
})

const filteredLogs = computed(() => {
  return logs.value.filter(log => {
    const level = (log.level || 'INFO').toUpperCase()
    return activeLevels.value.has(level)
  })
})

// Methods
const setMode = (newMode) => {
  if (mode.value === newMode) return
  mode.value = newMode
  logs.value = []
  totalLines.value = 0
  currentLineNum.value = 0
  progress.value = 0
  playing.value = true
  reconnect()
}

const togglePlay = () => {
  playing.value = !playing.value
  service.sendCommand(playing.value ? 'play' : 'pause')
}

const changeSpeed = () => {
  service.sendCommand('speed', speed.value)
}

const toggleLevel = (lvl) => {
  const next = new Set(activeLevels.value)
  if (next.has(lvl)) {
    next.delete(lvl)
  } else {
    next.add(lvl)
  }
  activeLevels.value = next
}

const clearLogs = () => {
  logs.value = []
}

const formatTime = (isoString) => {
  if (!isoString) return ''
  try {
    return new Date(isoString).toLocaleTimeString()
  } catch {
    return isoString
  }
}

const scrollToBottom = () => {
  if (autoScroll.value && logContainer.value) {
    nextTick(() => {
      logContainer.value.scrollTop = logContainer.value.scrollHeight
    })
  }
}

const reconnect = () => {
  service.disconnect()
  logs.value = []
  if (mode.value === 'replay') {
    service.connectReplay(props.analysisId, filterInput.value || null)
  } else {
    service.connect(props.analysisId, filterInput.value || null)
  }
}

// Lifecycle
onMounted(() => {
  service.onMessage((event) => {
    if (event.type === 'status') {
      status.value = event.payload
    } else if (event.type === 'meta') {
      totalLines.value = event.payload.total_lines || 0
    } else if (event.type === 'complete') {
      status.value = 'complete'
      playing.value = false
    } else if (event.type === 'log') {
      logs.value.push(event.payload)
      if (event.payload.line_num !== undefined) {
        currentLineNum.value = event.payload.line_num + 1
      }
      if (event.payload.progress !== undefined) {
        progress.value = event.payload.progress
      }
      // Keep buffer bounded
      if (logs.value.length > 2000) {
        logs.value = logs.value.slice(-1500)
      }
      scrollToBottom()
    } else if (event.type === 'error') {
      console.error('Log Viewer Error:', event.payload)
    }
  })

  reconnect()
})

onUnmounted(() => {
  service.disconnect()
})

watch(() => props.analysisId, () => {
  logs.value = []
  totalLines.value = 0
  currentLineNum.value = 0
  progress.value = 0
  reconnect()
})
</script>

<style scoped>
.live-log-viewer {
  background: var(--color-bg-tertiary, #1e1e1e);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  height: 550px;
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* Header */
.viewer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: var(--color-bg-secondary);
  border-bottom: 1px solid var(--color-border);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  flex-wrap: wrap;
  gap: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-left h3 {
  margin: 0;
  font-size: 13px;
  color: var(--color-text);
  font-weight: 600;
}

.line-counter {
  font-size: 11px;
  color: var(--color-text-dim);
}

.header-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

/* Status badge */
.status-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  background: var(--color-bg-tertiary, #333);
  color: var(--color-text-muted);
  text-transform: uppercase;
  font-weight: bold;
  letter-spacing: 0.5px;
}

.status-badge.connected {
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}

.status-badge.paused {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
}

.status-badge.complete {
  background: rgba(96, 165, 250, 0.15);
  color: #60a5fa;
}

/* Mode toggle */
.mode-toggle {
  display: flex;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.mode-btn {
  background: transparent;
  border: none;
  color: var(--color-text-muted);
  padding: 3px 10px;
  font-size: 11px;
  cursor: pointer;
  font-family: inherit;
}

.mode-btn.active {
  background: var(--color-primary, #3b82f6);
  color: white;
}

.mode-btn:hover:not(.active) {
  background: rgba(255, 255, 255, 0.05);
}

/* Controls */
.control-btn {
  background: var(--color-bg-tertiary, #333);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 11px;
  font-family: inherit;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.08);
}

.speed-select {
  background: var(--color-bg-tertiary, #333);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 3px 6px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-family: inherit;
  cursor: pointer;
}

/* Filter input */
.filter-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.filter-input {
  background: var(--color-bg-tertiary, #333);
  border: 1px solid var(--color-border);
  color: var(--color-text);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  width: 120px;
  font-family: inherit;
  transition: width 0.2s;
}

.filter-input:focus {
  width: 170px;
  outline: none;
  border-color: var(--color-primary);
}

/* Level filter buttons */
.level-filters {
  display: flex;
  gap: 2px;
}

.level-btn {
  background: transparent;
  border: 1px solid transparent;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: 0.3px;
}

.level-btn.level-critical { color: #f87171; }
.level-btn.level-error { color: #fb923c; }
.level-btn.level-warning { color: #facc15; }
.level-btn.level-info { color: #60a5fa; }
.level-btn.level-debug { color: #a78bfa; }

.level-btn.inactive {
  opacity: 0.3;
}

.level-btn:hover {
  border-color: var(--color-border);
}

/* Autoscroll */
.autoscroll-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--color-text-muted);
  cursor: pointer;
  user-select: none;
}

/* Progress bar */
.progress-bar {
  height: 2px;
  background: var(--color-bg-tertiary, #333);
  flex-shrink: 0;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary, #3b82f6);
  transition: width 0.3s ease;
}

/* Log container */
.log-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.empty-state {
  color: var(--color-text-dim);
  text-align: center;
  margin-top: 40px;
  font-style: italic;
  font-size: 12px;
}

/* Log entries */
.log-entry {
  display: flex;
  gap: 8px;
  padding: 1px 0;
  align-items: baseline;
}

.log-entry:hover {
  background: rgba(255, 255, 255, 0.02);
}

/* Severity row tinting */
.entry-critical,
.entry-error {
  background: rgba(248, 113, 113, 0.04);
}

.entry-warning {
  background: rgba(250, 204, 21, 0.03);
}

.line-num {
  color: var(--color-text-dim, #555);
  min-width: 40px;
  text-align: right;
  flex-shrink: 0;
  user-select: none;
  font-size: 11px;
}

.level-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 0 5px;
  border-radius: 3px;
  flex-shrink: 0;
  min-width: 52px;
  text-align: center;
}

.badge-critical { background: rgba(248, 113, 113, 0.2); color: #f87171; }
.badge-error    { background: rgba(251, 146, 60, 0.2);  color: #fb923c; }
.badge-warning  { background: rgba(250, 204, 21, 0.15); color: #facc15; }
.badge-info     { background: rgba(96, 165, 250, 0.15); color: #60a5fa; }
.badge-debug    { background: rgba(167, 139, 250, 0.15); color: #a78bfa; }

.timestamp {
  color: var(--color-text-dim, #6b7280);
  flex-shrink: 0;
  font-size: 11px;
}

.source {
  color: var(--color-info, #569cd6);
  flex-shrink: 0;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
}

.message {
  white-space: pre-wrap;
  word-break: break-all;
  color: var(--color-text);
}

/* Scrollbar */
.log-container::-webkit-scrollbar {
  width: 10px;
}

.log-container::-webkit-scrollbar-track {
  background: var(--color-bg-tertiary, #1e1e1e);
}

.log-container::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 5px;
  border: 2px solid var(--color-bg-tertiary, #1e1e1e);
}

.log-container::-webkit-scrollbar-thumb:hover {
  background: var(--color-border-hover);
}
</style>
