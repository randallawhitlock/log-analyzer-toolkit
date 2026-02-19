<template>
  <div class="analysis-view">
    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading analysis...</p>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="error-state">
      <span class="error-icon">⚠️</span>
      <h2>Failed to load analysis</h2>
      <p>{{ error }}</p>
      <router-link to="/" class="back-btn">← Back to Home</router-link>
    </div>

    <!-- Analysis Content -->
    <div v-else-if="analysis" class="analysis-content">
      <!-- Header -->
      <header class="analysis-header">
        <router-link to="/" class="back-link">← Back</router-link>
        <div class="header-content">
          <h1>{{ analysis.filename }}</h1>
          <div class="header-meta">
            <span class="format-badge">{{ analysis.detected_format }}</span>
            <span class="date">Analyzed {{ formatDate(analysis.created_at) }}</span>
          </div>
        </div>
        <div class="header-actions">
          <button @click="exportJSON" class="export-btn" title="Download analysis as JSON">
            📥 Export
          </button>
          <button @click="toggleLiveTail" class="live-btn" :class="{ active: showLiveTail }">
            {{ showLiveTail ? '✕ Close Viewer' : '▶ Log Viewer' }}
          </button>
          <button @click="runTriageAnalysis" :disabled="triageLoading" class="triage-btn" :class="{'scanning': triageLoading}">
            <div v-if="triageLoading" class="scanline"></div>
            {{ triageLoading ? 'Analyzing Logs...' : '🤖 Run AI Triage' }}
          </button>
          <button @click="deleteCurrentAnalysis" class="delete-btn" title="Delete analysis">
            🗑️
          </button>
        </div>
      </header>

      <!-- Stats Grid -->
      <section class="stats-grid animate-slide-up stagger-1">
        <StatCard
          title="Total Lines"
          :value="analysis.total_lines"
          icon="📄"
          format="number"
        />
        <StatCard
          title="Parse Rate"
          :value="analysis.parse_success_rate"
          icon="✓"
          format="percent"
          :color="getSuccessColor(analysis.parse_success_rate)"
        />
        <StatCard
          title="Error Rate"
          :value="analysis.error_rate"
          icon="⚠️"
          format="percent"
          :color="getErrorColor(analysis.error_rate)"
        />
        <StatCard
          v-if="analysis.time_span"
          title="Time Span"
          :value="analysis.time_span"
          icon="⏱️"
        />
      </section>

      <!-- Live Log Viewer -->
      <section v-if="showLiveTail" class="panel live-section">
        <LiveLogViewer :analysis-id="analysis.id" />
      </section>

      <!-- Main Content Grid -->
      <div v-else class="content-grid animate-slide-up stagger-2">
        <!-- Level Chart -->
        <LevelChart :level-counts="analysis.level_counts" />

        <!-- Top Errors -->
        <section v-if="topErrors.length > 0" class="panel top-errors">
          <h3>Top Errors</h3>
          <ul class="error-list">
            <li v-for="(item, idx) in topErrors" :key="idx" class="error-item">
              <span class="error-count">{{ item[1] }}×</span>
              <span class="error-message">{{ truncate(item[0], 120) }}</span>
            </li>
          </ul>
        </section>

        <!-- Status Codes (for HTTP logs) -->
        <section v-if="hasStatusCodes" class="panel status-codes">
          <h3>HTTP Status Codes</h3>
          <div class="status-grid">
            <div
              v-for="(count, code) in analysis.status_codes"
              :key="code"
              class="status-item"
              :class="getStatusClass(code)"
            >
              <span class="status-code">{{ code }}</span>
              <span class="status-count">{{ count.toLocaleString() }}</span>
            </div>
          </div>
        </section>
      </div>

      <!-- Log Sample Preview -->
      <section class="panel log-sample-section animate-slide-up stagger-3">
        <div class="section-header-row">
          <h3>📋 Log Sample Preview</h3>
          <button @click="toggleSample" class="toggle-btn">
            {{ showSample ? '▲ Hide' : '▼ Show' }}
          </button>
        </div>
        <div v-if="showSample" class="log-sample">
          <div v-if="loadingSamples" class="sample-loading">
            Loading log samples...
          </div>
          <div v-else-if="logSamples.length > 0" class="sample-lines">
            <div v-for="(line, idx) in logSamples" :key="idx" class="log-line">
              <span class="line-num">{{ idx + 1 }}</span>
              <span class="line-content">{{ line }}</span>
            </div>
          </div>
          <div v-else class="no-samples">No sample data available</div>
        </div>
      </section>

      <!-- Triage Results -->
      <section v-if="triage" class="triage-section animate-slide-up stagger-4">
        <h2>
          <span class="section-icon">🤖</span>
          AI Triage Results
        </h2>

        <div class="triage-header">
          <div class="severity-badge" :class="`severity-${triage.overall_severity.toLowerCase()}`">
            {{ triage.overall_severity }}
          </div>
          <div class="triage-meta">
            <span>Confidence: {{ (triage.confidence * 100).toFixed(0) }}%</span>
            <span class="dot">•</span>
            <span>Provider: {{ triage.provider_used }}</span>
          </div>
        </div>

        <div class="triage-summary markdown-content" v-html="renderMarkdown(triage.summary)"></div>

        <div v-if="triage.issues && triage.issues.length > 0" class="issues-list">
          <h3>Identified Issues</h3>
          <div v-for="(issue, idx) in triage.issues" :key="idx" class="issue-card">
            <div class="issue-header">
              <span class="issue-severity" :class="`severity-${issue.severity?.toLowerCase()}`">
                {{ issue.severity }}
              </span>
              <span v-if="issue.category && issue.category !== 'unknown'" class="issue-category">
                {{ formatCategory(issue.category) }}
              </span>
              <span class="issue-title">{{ issue.title }}</span>
            </div>
            <div class="issue-description markdown-content" v-html="renderMarkdown(issue.description)"></div>

            <!-- Root Cause Analysis -->
            <div v-if="issue.root_cause_analysis" class="issue-root-cause">
              <strong>🔬 Root Cause Analysis:</strong>
              <div class="markdown-content" v-html="renderMarkdown(issue.root_cause_analysis)"></div>
            </div>

            <!-- Evidence -->
            <div v-if="issue.evidence && issue.evidence.length > 0" class="issue-evidence">
              <strong>📋 Evidence:</strong>
              <ul class="evidence-list">
                <li v-for="(item, i) in issue.evidence" :key="i">{{ item }}</li>
              </ul>
            </div>
            <div v-if="issue.recommendation" class="issue-recommendation">
              <strong>💡 Recommendation:</strong>
              <div class="markdown-content" v-html="renderMarkdown(issue.recommendation)"></div>
            </div>
            <div class="issue-actions">
              <button
                @click="runDeepDive(idx, issue)"
                :disabled="deepDiveLoading[idx]"
                class="deep-dive-btn"
              >
                <span v-if="deepDiveLoading[idx]" class="btn-spinner"></span>
                {{ deepDiveLoading[idx] ? 'Analyzing...' : '🔬 Deep Dive' }}
              </button>
            </div>
            <div v-if="deepDiveResults[idx]" class="deep-dive-panel">
              <div class="deep-dive-header">
                <h4>🔬 Deep Dive Analysis</h4>
                <span class="deep-dive-meta">
                  {{ deepDiveResults[idx].provider_used }} · {{ deepDiveResults[idx].model_used }} · {{ (deepDiveResults[idx].analysis_time_ms / 1000).toFixed(1) }}s
                </span>
              </div>
              <div class="deep-dive-content markdown-content" v-html="renderMarkdown(deepDiveResults[idx].detailed_analysis)"></div>
            </div>
          </div>
        </div>
      </section>
    </div>

    <!-- Custom Delete Modal -->
    <div v-if="showDeleteModal" class="modal-overlay">
      <div class="modal-content">
        <h3>Confirm Deletion</h3>
        <p>Are you sure you want to delete this analysis?</p>
        <div class="modal-actions">
          <button @click="showDeleteModal = false" class="cancel-btn">Cancel</button>
          <button @click="executeDelete" class="confirm-btn">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import StatCard from '../components/StatCard.vue'
import LevelChart from '../components/LevelChart.vue'
import LiveLogViewer from '../components/LiveLogViewer.vue'
import { useApi } from '../composables/useApi'

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
})

const renderMarkdown = (text) => {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text))
}

const route = useRoute()
const router = useRouter()
const {
  getAnalysis,
  deleteAnalysis,
  runTriage,
  getTriagesForAnalysis,
  deepDiveIssue,
  getLogPreview,
  loading,
  error
} = useApi()

const analysis = ref(null)
const triage = ref(null)
const triageLoading = ref(false)
const showSample = ref(false)
const showLiveTail = ref(false)
const loadingSamples = ref(false)
const logSamples = ref([])
const deepDiveLoading = ref({})
const deepDiveResults = ref({})
const showDeleteModal = ref(false)
let pollInterval = null

const topErrors = computed(() => {
  return analysis.value?.top_errors?.slice(0, 10) || []
})

const hasStatusCodes = computed(() => {
  const codes = analysis.value?.status_codes
  return codes && Object.keys(codes).length > 0
})

const getSuccessColor = (rate) => {
  if (rate >= 95) return 'success'
  if (rate >= 80) return 'warning'
  return 'error'
}

const getErrorColor = (rate) => {
  if (rate <= 1) return 'success'
  if (rate <= 5) return 'warning'
  return 'error'
}

const getStatusClass = (code) => {
  const c = parseInt(code)
  if (c >= 200 && c < 300) return 'status-2xx'
  if (c >= 300 && c < 400) return 'status-3xx'
  if (c >= 400 && c < 500) return 'status-4xx'
  if (c >= 500) return 'status-5xx'
  return ''
}

const formatDate = (dateStr) => {
  if (!dateStr) return 'Unknown'
  // Append 'Z' to indicate UTC if not present
  const utcStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`
  return new Date(utcStr).toLocaleString()
}

const truncate = (str, len) => {
  if (!str || str.length <= len) return str
  return str.substring(0, len) + '...'
}

const formatCategory = (category) => {
  if (!category) return ''
  return category.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')
}

const runTriageAnalysis = async () => {
  try {
    triageLoading.value = true
    const result = await runTriage(route.params.id)
    triage.value = result
    // Reset deep dive results when re-running triage
    deepDiveLoading.value = {}
    deepDiveResults.value = {}
  } catch (err) {
    console.error('Triage failed:', err)
    alert('Failed to run triage: ' + (err.message || 'Unknown error'))
  } finally {
    triageLoading.value = false
  }
}

const runDeepDive = async (idx, issue) => {
  try {
    deepDiveLoading.value = { ...deepDiveLoading.value, [idx]: true }
    const result = await deepDiveIssue({
      analysis_id: route.params.id,
      issue_title: issue.title,
      issue_description: issue.description || '',
      issue_severity: issue.severity || 'MEDIUM',
      issue_recommendation: issue.recommendation || '',
      affected_components: issue.affected_components || [],
    })
    deepDiveResults.value = { ...deepDiveResults.value, [idx]: result }
  } catch (err) {
    console.error('Deep dive failed:', err)
    alert('Deep dive failed: ' + (err.response?.data?.detail || err.message || 'Unknown error'))
  } finally {
    deepDiveLoading.value = { ...deepDiveLoading.value, [idx]: false }
  }
}

const deleteCurrentAnalysis = () => {
  showDeleteModal.value = true
}

const executeDelete = async () => {
  try {
    await deleteAnalysis(route.params.id)
    showDeleteModal.value = false
    router.push('/')
  } catch (err) {
    console.error('Delete failed:', err)
    alert('Failed to delete: ' + (err.message || 'Unknown error'))
  }
}

/**
 * Export analysis data as JSON file
 */
const exportJSON = () => {
  if (!analysis.value) return

  const exportData = {
    filename: analysis.value.filename,
    detected_format: analysis.value.detected_format,
    analyzed_at: analysis.value.created_at,
    statistics: {
      total_lines: analysis.value.total_lines,
      parsed_lines: analysis.value.parsed_lines,
      failed_lines: analysis.value.failed_lines,
      parse_success_rate: analysis.value.parse_success_rate,
      error_rate: analysis.value.error_rate
    },
    level_counts: analysis.value.level_counts,
    top_errors: analysis.value.top_errors,
    top_sources: analysis.value.top_sources,
    status_codes: analysis.value.status_codes,
    time_range: {
      earliest: analysis.value.earliest_timestamp,
      latest: analysis.value.latest_timestamp,
      span: analysis.value.time_span
    },
    triage: triage.value || null
  }

  const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `analysis_${analysis.value.filename.replace(/\.[^/.]+$/, '')}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/**
 * Toggle log sample visibility and load samples if needed
 */
const toggleSample = () => {
  showSample.value = !showSample.value
  if (showSample.value && logSamples.value.length === 0) {
    loadLogSamples()
  }
}

/**
 * Load sample log lines from the backend preview endpoint.
 */
const loadLogSamples = async () => {
  loadingSamples.value = true
  try {
    const data = await getLogPreview(route.params.id, 50)
    logSamples.value = data.lines.length > 0 ? data.lines : ['No sample log lines available']
  } catch (err) {
    console.error('Failed to load log samples:', err)
    logSamples.value = ['Failed to load log samples']
  } finally {
    loadingSamples.value = false
  }
}

const toggleLiveTail = () => {
  showLiveTail.value = !showLiveTail.value
}

onMounted(async () => {
  try {
    analysis.value = await getAnalysis(route.params.id)

    if (analysis.value?.detected_format === 'pending') {
      pollInterval = setInterval(async () => {
        try {
          const updated = await getAnalysis(route.params.id)
          if (updated.detected_format !== 'pending') {
            analysis.value = updated
            clearInterval(pollInterval)
          }
        } catch (e) {
          console.error('Polling failed', e)
        }
      }, 2000)
    }

    // Check for existing triages
    const triages = await getTriagesForAnalysis(route.params.id)
    if (triages && triages.length > 0) {
      triage.value = triages[0] // Most recent (API returns newest first)
    }
  } catch (err) {
    console.error('Failed to load analysis:', err)
  }
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.analysis-view {
  max-width: 1060px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.loading-state,
.error-state {
  text-align: center;
  padding: 80px var(--spacing-lg);
}

.spinner,
.btn-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border-width: 2px;
  display: inline-block;
  margin-right: 6px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 40px;
  display: block;
  margin-bottom: 16px;
  opacity: 0.7;
}

.back-btn {
  display: inline-block;
  margin-top: 16px;
  padding: 8px 18px;
  background: var(--color-primary);
  color: white;
  text-decoration: none;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: 13px;
}

/* Header */
.analysis-header {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  position: sticky;
  top: 80px;
  z-index: 50;
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  padding: var(--spacing-md) var(--spacing-lg);
  border-radius: var(--radius-xl);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-md);
  transition: all var(--transition-spring);
}

.back-link {
  color: var(--color-text-muted);
  text-decoration: none;
  padding: 8px 0;
  font-size: 13px;
}

.back-link:hover {
  color: var(--color-primary);
}

.header-content {
  flex: 1;
}

.header-content h1 {
  margin: 0 0 6px 0;
  font-size: 1.5rem;
  word-break: break-word;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.format-badge {
  background: var(--color-bg-tertiary);
  padding: 3px 10px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.header-actions {
  display: flex;
  gap: 6px;
}

.triage-btn,
.delete-btn {
  padding: 8px 14px;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.triage-btn {
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  color: white;
  position: relative;
  overflow: hidden;
}

.triage-btn.scanning {
  background: var(--color-bg-tertiary);
  color: var(--color-primary);
  border: 1px solid var(--color-primary);
  pointer-events: none;
}

.scanline {
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 6px;
  background: var(--color-primary-glow);
  box-shadow: 0 0 12px var(--color-primary);
  animation: scanline 1.5s linear infinite;
}

.triage-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: var(--shadow-md);
}

.triage-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.delete-btn {
  background: var(--color-bg-tertiary);
  color: var(--color-text-muted);
}

.delete-btn:hover {
  background: var(--color-error);
  color: white;
}

.live-btn {
  padding: 8px 14px;
  border: 1px solid var(--color-error);
  background: transparent;
  color: var(--color-error);
  border-radius: var(--radius-md);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.live-btn:hover,
.live-btn.active {
  background: var(--color-error);
  color: white;
}

.live-section {
  margin-bottom: var(--spacing-xl);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 12px;
  margin-bottom: var(--spacing-xl);
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.panel {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.panel h3 {
  margin: 0 0 14px 0;
  font-size: 14px;
  font-weight: 600;
}

/* Error List */
.error-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-item {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 12px;
}

.error-count {
  color: var(--color-error);
  font-weight: 700;
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}

.error-message {
  color: var(--color-text-muted);
  word-break: break-word;
}

/* Status Codes */
.status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 14px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  min-width: 64px;
}

.status-code {
  font-weight: 700;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.status-count {
  font-size: 11px;
  color: var(--color-text-dim);
  font-variant-numeric: tabular-nums;
}

.status-2xx .status-code { color: var(--color-success); }
.status-3xx .status-code { color: var(--color-info); }
.status-4xx .status-code { color: var(--color-warning); }
.status-5xx .status-code { color: var(--color-error); }

/* Triage Section */
.triage-section {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-lg);
}

.triage-section h2 {
  margin: 0 0 var(--spacing-md) 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1.125rem;
}

.section-icon {
  font-size: 20px;
}

.triage-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}

.severity-badge {
  padding: 4px 14px;
  border-radius: var(--radius-full);
  font-weight: 700;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.severity-critical { background: var(--color-error); color: white; }
.severity-high { background: var(--color-warning); color: #18181b; }
.severity-medium { background: #eab308; color: #18181b; }
.severity-low { background: var(--color-info); color: white; }
.severity-healthy { background: var(--color-success); color: white; }

.triage-meta {
  font-size: 12px;
  color: var(--color-text-dim);
  display: flex;
  gap: 8px;
}

.dot {
  opacity: 0.3;
}

.triage-summary {
  padding: 14px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  line-height: 1.6;
  margin-bottom: var(--spacing-lg);
  font-size: 14px;
}

.issues-list h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
}

.issue-card {
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-lg);
  padding: 16px;
  margin-bottom: 10px;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.issue-severity {
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.issue-category {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  color: var(--color-text-dim);
}

.issue-title {
  font-weight: 600;
  font-size: 14px;
}

.issue-description {
  margin: 0 0 12px 0;
  color: var(--color-text-muted);
  line-height: 1.5;
  font-size: 13px;
}

.issue-root-cause {
  margin: 12px 0;
  padding: 12px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
}

.issue-root-cause strong {
  display: block;
  margin-bottom: 6px;
  color: var(--color-primary);
  font-size: 12px;
}

.issue-evidence {
  margin: 12px 0;
}

.issue-evidence strong {
  display: block;
  margin-bottom: 6px;
  color: var(--color-text);
  font-size: 12px;
}

.evidence-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.evidence-list li {
  margin-bottom: 4px;
}

.issue-recommendation {
  padding: 12px;
  background: var(--color-primary-light);
  border-radius: var(--radius-md);
  border-left: 3px solid var(--color-primary);
  font-size: 13px;
}

/* Markdown Content Styles */
.markdown-content :deep(p) {
  margin: 0 0 8px 0;
  line-height: 1.6;
  font-size: 13px;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
  font-size: 13px;
}

.markdown-content :deep(li) {
  margin-bottom: 4px;
  line-height: 1.5;
}

.markdown-content :deep(code) {
  background: var(--color-primary-light);
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: 0.85em;
}

.markdown-content :deep(pre) {
  background: var(--color-bg-tertiary);
  padding: 12px;
  border-radius: var(--radius-md);
  overflow-x: auto;
  margin: 8px 0;
  border: 1px solid var(--color-border);
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
  border: none;
}

.markdown-content :deep(strong) {
  color: var(--color-text);
}

.markdown-content :deep(a) {
  color: var(--color-primary);
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--color-border);
  margin: 8px 0;
  padding: 4px 12px;
  color: var(--color-text-muted);
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 12px 0 6px 0;
  font-size: 1em;
  font-weight: 600;
}

/* Deep Dive */
.issue-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.deep-dive-btn {
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-muted);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: 4px;
}

.deep-dive-btn:hover:not(:disabled) {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
  color: var(--color-text);
}

.deep-dive-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.deep-dive-panel {
  margin-top: 14px;
  padding: 16px;
  background: var(--color-primary-light);
  border: 1px solid rgba(99, 102, 241, 0.2);
  border-radius: var(--radius-lg);
}

.deep-dive-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.deep-dive-header h4 {
  margin: 0;
  font-size: 14px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.deep-dive-meta {
  font-size: 10px;
  color: var(--color-text-dim);
}

.deep-dive-content {
  font-size: 13px;
  line-height: 1.7;
}

/* Export Button */
.export-btn {
  padding: 8px 14px;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.export-btn:hover {
  background: var(--color-success);
  border-color: var(--color-success);
  color: white;
}

/* Log Sample Section */
.log-sample-section {
  margin-bottom: var(--spacing-lg);
}

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header-row h3 {
  margin: 0;
  font-size: 14px;
}

.toggle-btn {
  padding: 5px 10px;
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
  font-size: 11px;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.toggle-btn:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.log-sample {
  margin-top: 14px;
}

.sample-loading {
  text-align: center;
  padding: 20px;
  color: var(--color-text-muted);
  font-size: 13px;
}

.sample-lines {
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  padding: 10px;
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
}

.log-line {
  display: flex;
  gap: 10px;
  padding: 4px 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  border-bottom: 1px solid var(--color-border);
}

.log-line:last-child {
  border-bottom: none;
}

.log-line:hover {
  background: var(--color-bg-hover);
}

.line-num {
  color: var(--color-text-dim);
  min-width: 20px;
  text-align: right;
  flex-shrink: 0;
  user-select: none;
}

.line-content {
  color: var(--color-text-muted);
  word-break: break-word;
  white-space: pre-wrap;
}

.no-samples {
  text-align: center;
  padding: 20px;
  color: var(--color-text-dim);
  font-size: 13px;
}
</style>
