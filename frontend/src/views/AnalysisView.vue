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
            🔴 Live Tail
          </button>
          <button @click="runTriageAnalysis" :disabled="triageLoading" class="triage-btn">
            <span v-if="triageLoading" class="btn-spinner"></span>
            {{ triageLoading ? 'Running...' : '🤖 Run AI Triage' }}
          </button>
          <button @click="deleteCurrentAnalysis" class="delete-btn" title="Delete analysis">
            🗑️
          </button>
        </div>
      </header>

      <!-- Stats Grid -->
      <section class="stats-grid">
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
        <LiveLogViewer :file-path="analysis.file_path" />
      </section>

      <!-- Main Content Grid -->
      <div v-else class="content-grid">
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
      <section class="panel log-sample-section">
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
      <section v-if="triage" class="triage-section">
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
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

const deleteCurrentAnalysis = async () => {
  if (!confirm('Are you sure you want to delete this analysis?')) return

  try {
    await deleteAnalysis(route.params.id)
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
 * Load sample log lines (simulated - in real app would call backend)
 */
const loadLogSamples = () => {
  loadingSamples.value = true
  // Simulate loading - in production, this would fetch from backend
  setTimeout(() => {
    // Use top_errors as sample data since we don't have raw lines endpoint
    const samples = analysis.value?.top_errors?.slice(0, 10).map(e => e[0]) || []
    logSamples.value = samples.length > 0 ? samples : ['No sample log lines available']
    loadingSamples.value = false
  }, 300)
}

const toggleLiveTail = () => {
  showLiveTail.value = !showLiveTail.value
}

onMounted(async () => {
  try {
    analysis.value = await getAnalysis(route.params.id)

    // Check for existing triages
    const triages = await getTriagesForAnalysis(route.params.id)
    if (triages && triages.length > 0) {
      triage.value = triages[triages.length - 1] // Most recent
    }
  } catch (err) {
    console.error('Failed to load analysis:', err)
  }
})
</script>

<style scoped>
.analysis-view {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

.loading-state,
.error-state {
  text-align: center;
  padding: 80px 24px;
}

.spinner,
.btn-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border, #3a3a55);
  border-top-color: var(--color-primary, #646cff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

.btn-spinner {
  width: 16px;
  height: 16px;
  border-width: 2px;
  display: inline-block;
  margin-right: 8px;
  vertical-align: middle;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.back-btn {
  display: inline-block;
  margin-top: 16px;
  padding: 10px 20px;
  background: var(--color-primary, #646cff);
  color: white;
  text-decoration: none;
  border-radius: 8px;
}

/* Header */
.analysis-header {
  display: flex;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}

.back-link {
  color: var(--color-text-muted, #888);
  text-decoration: none;
  padding: 8px 0;
}

.back-link:hover {
  color: var(--color-primary, #646cff);
}

.header-content {
  flex: 1;
}

.header-content h1 {
  margin: 0 0 8px 0;
  font-size: 1.75rem;
  word-break: break-word;
}

.header-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--color-text-muted, #888);
  font-size: 14px;
}

.format-badge {
  background: var(--color-bg-tertiary, #2a2a4e);
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 600;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.triage-btn,
.delete-btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.triage-btn {
  background: linear-gradient(135deg, var(--color-primary, #646cff), var(--color-secondary, #9c27b0));
  color: white;
}

.triage-btn:hover:not(:disabled) {
  transform: translateY(-2px);
}

.triage-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.delete-btn {
  background: var(--color-bg-tertiary, #2a2a4e);
}

.delete-btn:hover {
  background: var(--color-error, #f44336);
}

.live-btn {
  padding: 10px 16px;
  border: 1px solid var(--color-error, #f44336);
  background: transparent;
  color: var(--color-error, #f44336);
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.live-btn:hover,
.live-btn.active {
  background: var(--color-error, #f44336);
  color: white;
}

.live-section {
  margin-bottom: 32px;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

/* Content Grid */
.content-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 24px;
  margin-bottom: 32px;
}

.panel {
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 12px;
  padding: 20px;
}

.panel h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
}

/* Error List */
.error-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.error-item {
  display: flex;
  gap: 12px;
  padding: 10px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 8px;
  font-size: 13px;
}

.error-count {
  color: var(--color-error, #f44336);
  font-weight: 600;
  flex-shrink: 0;
}

.error-message {
  color: var(--color-text-muted, #aaa);
  word-break: break-word;
}

/* Status Codes */
.status-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.status-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 16px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 8px;
  min-width: 70px;
}

.status-code {
  font-weight: 700;
  font-size: 18px;
}

.status-count {
  font-size: 12px;
  color: var(--color-text-muted, #888);
}

.status-2xx .status-code { color: var(--color-success, #4caf50); }
.status-3xx .status-code { color: var(--color-info, #2196f3); }
.status-4xx .status-code { color: var(--color-warning, #ff9800); }
.status-5xx .status-code { color: var(--color-error, #f44336); }

/* Triage Section */
.triage-section {
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 16px;
  padding: 24px;
}

.triage-section h2 {
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-icon {
  font-size: 24px;
}

.triage-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.severity-badge {
  padding: 6px 16px;
  border-radius: 20px;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
}

.severity-critical { background: var(--color-error, #f44336); color: white; }
.severity-high { background: var(--color-warning, #ff9800); color: black; }
.severity-medium { background: #ffc107; color: black; }
.severity-low { background: var(--color-info, #2196f3); color: white; }
.severity-healthy { background: var(--color-success, #4caf50); color: white; }

.triage-meta {
  font-size: 13px;
  color: var(--color-text-muted, #888);
  display: flex;
  gap: 8px;
}

.dot {
  opacity: 0.5;
}

.triage-summary {
  padding: 16px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 8px;
  line-height: 1.6;
  margin-bottom: 24px;
}

.issues-list h3 {
  margin: 0 0 16px 0;
}

.issue-card {
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.issue-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.issue-severity {
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.issue-category {
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  color: var(--color-text-muted, #aaa);
}

.issue-title {
  font-weight: 600;
}

.issue-description {
  margin: 0 0 12px 0;
  color: var(--color-text-muted, #aaa);
  line-height: 1.5;
}

.issue-root-cause {
  margin: 12px 0;
  padding: 12px;
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
}

.issue-root-cause strong {
  display: block;
  margin-bottom: 8px;
  color: var(--color-primary, #646cff);
}

.issue-evidence {
  margin: 12px 0;
}

.issue-evidence strong {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text, #fff);
}

.evidence-list {
  margin: 0;
  padding-left: 20px;
  color: var(--color-text-muted, #aaa);
}

.evidence-list li {
  margin-bottom: 4px;
}

.issue-recommendation {
  padding: 12px;
  background: rgba(100, 108, 255, 0.1);
  border-radius: 8px;
  border-left: 3px solid var(--color-primary, #646cff);
  font-size: 13px;
}

/* Markdown Content Styles */
.markdown-content :deep(p) {
  margin: 0 0 8px 0;
  line-height: 1.6;
}

.markdown-content :deep(p:last-child) {
  margin-bottom: 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content :deep(li) {
  margin-bottom: 4px;
  line-height: 1.5;
}

.markdown-content :deep(code) {
  background: rgba(100, 108, 255, 0.15);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: var(--font-mono, monospace);
  font-size: 0.9em;
}

.markdown-content :deep(pre) {
  background: var(--color-bg-tertiary, #2a2a4e);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
}

.markdown-content :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-content :deep(strong) {
  color: var(--color-text, #fff);
}

.markdown-content :deep(a) {
  color: var(--color-primary, #646cff);
  text-decoration: none;
}

.markdown-content :deep(a:hover) {
  text-decoration: underline;
}

.markdown-content :deep(blockquote) {
  border-left: 3px solid var(--color-border, #3a3a55);
  margin: 8px 0;
  padding: 4px 12px;
  color: var(--color-text-muted, #aaa);
}

.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 12px 0 8px 0;
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
  padding: 8px 16px;
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
  background: transparent;
  color: var(--color-text-muted, #aaa);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.deep-dive-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, rgba(100, 108, 255, 0.15), rgba(156, 39, 176, 0.15));
  border-color: var(--color-primary, #646cff);
  color: var(--color-text, #fff);
}

.deep-dive-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.deep-dive-panel {
  margin-top: 16px;
  padding: 20px;
  background: linear-gradient(135deg, rgba(100, 108, 255, 0.05), rgba(156, 39, 176, 0.05));
  border: 1px solid rgba(100, 108, 255, 0.2);
  border-radius: 12px;
}

.deep-dive-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--color-border, #3a3a55);
}

.deep-dive-header h4 {
  margin: 0;
  font-size: 15px;
  background: linear-gradient(135deg, var(--color-primary, #646cff), var(--color-secondary, #9c27b0));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.deep-dive-meta {
  font-size: 11px;
  color: var(--color-text-dim, #666);
}

.deep-dive-content {
  font-size: 14px;
  line-height: 1.7;
}

/* Export Button */
.export-btn {
  padding: 10px 16px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
  color: var(--color-text, #fff);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.export-btn:hover {
  background: var(--color-success, #4caf50);
  border-color: var(--color-success, #4caf50);
}

/* Log Sample Section */
.log-sample-section {
  margin-bottom: 24px;
}

.section-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-header-row h3 {
  margin: 0;
}

.toggle-btn {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 6px;
  color: var(--color-text-muted, #888);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toggle-btn:hover {
  border-color: var(--color-primary, #646cff);
  color: var(--color-primary, #646cff);
}

.log-sample {
  margin-top: 16px;
}

.sample-loading {
  text-align: center;
  padding: 24px;
  color: var(--color-text-muted, #888);
}

.sample-lines {
  background: var(--color-bg-tertiary, #2a2a4e);
  border-radius: 8px;
  padding: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.log-line {
  display: flex;
  gap: 12px;
  padding: 6px 8px;
  font-family: var(--font-mono, monospace);
  font-size: 12px;
  border-bottom: 1px solid var(--color-border, #3a3a55);
}

.log-line:last-child {
  border-bottom: none;
}

.line-num {
  color: var(--color-text-dim, #666);
  min-width: 24px;
  text-align: right;
  flex-shrink: 0;
}

.line-content {
  color: var(--color-text-muted, #aaa);
  word-break: break-word;
  white-space: pre-wrap;
}

.no-samples {
  text-align: center;
  padding: 24px;
  color: var(--color-text-dim, #666);
}
</style>
