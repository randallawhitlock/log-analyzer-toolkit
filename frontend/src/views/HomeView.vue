<template>
  <div class="home-view">
    <header class="hero">
      <div class="hero-badge">Intelligent Log Analysis</div>
      <h1 class="hero-title">
        Log Analyzer <span class="accent">Pro</span>
      </h1>
      <p class="hero-subtitle">
        Upload, analyze, and troubleshoot log files with AI-powered insights.
      </p>
    </header>

    <section class="upload-section">
      <LogUpload @upload-complete="handleUploadComplete" />
    </section>

    <section class="recent-section" v-if="recentAnalyses.length > 0">
      <div class="section-header">
        <h2>Recent Analyses</h2>
        <router-link to="/analyses" class="view-all">
          View all
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M5 12h14M12 5l7 7-7 7"/>
          </svg>
        </router-link>
      </div>

      <div class="recent-grid">
        <router-link
          v-for="analysis in recentAnalyses"
          :key="analysis.id"
          :to="`/analysis/${analysis.id}`"
          class="recent-card"
        >
          <div class="card-header">
            <span class="format-badge">{{ analysis.detected_format }}</span>
            <span class="success-rate" :class="getSuccessClass(analysis.parse_success_rate)">
              {{ analysis.parse_success_rate.toFixed(1) }}%
            </span>
          </div>
          <h3 class="card-title">{{ analysis.filename }}</h3>
          <div class="card-meta">
            <span>{{ analysis.total_lines.toLocaleString() }} lines</span>
            <span class="separator">/</span>
            <span>{{ formatDate(analysis.created_at) }}</span>
          </div>
        </router-link>
      </div>
    </section>

    <section class="features-section">
      <h2 class="features-title">What you can do</h2>
      <div class="features-grid">
        <div class="feature-card">
          <div class="feature-icon-wrapper icon-detect">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <h3>Auto-Detection</h3>
          <p>Automatically detects 15+ log formats including Apache, Nginx, Syslog, JSON, and more.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon-wrapper icon-analyze">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <path d="M3 3v18h18"/>
              <path d="m7 16 4-8 4 5 5-10"/>
            </svg>
          </div>
          <h3>Deep Analysis</h3>
          <p>Extract error patterns, severity breakdowns, time analysis, and key metrics at a glance.</p>
        </div>
        <div class="feature-card">
          <div class="feature-icon-wrapper icon-ai">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z"/>
              <circle cx="9" cy="14" r="1" fill="currentColor"/>
              <circle cx="15" cy="14" r="1" fill="currentColor"/>
            </svg>
          </div>
          <h3>AI-Powered Triage</h3>
          <p>Get intelligent root cause analysis and recommendations powered by multiple AI providers.</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LogUpload from '../components/LogUpload.vue'
import { useApi } from '../composables/useApi'

const { getAnalyses } = useApi()
const recentAnalyses = ref([])

const handleUploadComplete = (analysis) => {
  console.log('Upload complete:', analysis.id)
}

const getSuccessClass = (rate) => {
  if (rate >= 90) return 'success'
  if (rate >= 70) return 'warning'
  return 'error'
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`
  return date.toLocaleDateString()
}

onMounted(async () => {
  try {
    const data = await getAnalyses({ limit: 4 })
    recentAnalyses.value = data.analyses
  } catch (error) {
    console.error('Failed to load recent analyses:', error)
  }
})
</script>

<style scoped>
.home-view {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.hero {
  text-align: center;
  margin-bottom: var(--spacing-3xl);
}

.hero-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: var(--radius-full);
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border: 1px solid rgba(99, 102, 241, 0.2);
  margin-bottom: var(--spacing-md);
}

.hero-title {
  font-size: 3rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin: 0;
}

.accent {
  background: linear-gradient(135deg, var(--color-primary), var(--color-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.1rem;
  color: var(--color-text-muted);
  margin-top: 12px;
  max-width: 480px;
  margin-left: auto;
  margin-right: auto;
}

.upload-section {
  margin-bottom: var(--spacing-3xl);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
}

.section-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.view-all {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--color-text-muted);
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
  transition: color var(--transition-fast);
}

.view-all:hover {
  color: var(--color-primary);
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 12px;
}

.recent-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-normal);
}

.recent-card:hover {
  border-color: var(--color-border-active);
  box-shadow: var(--shadow-glow);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.format-badge {
  background: var(--color-bg-tertiary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  font-size: 10px;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--color-text-muted);
}

.success-rate {
  font-weight: 700;
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.success-rate.success { color: var(--color-success); }
.success-rate.warning { color: var(--color-warning); }
.success-rate.error { color: var(--color-error); }

.card-title {
  margin: 0 0 6px 0;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 11px;
  color: var(--color-text-dim);
  display: flex;
  align-items: center;
  gap: 6px;
}

.separator {
  opacity: 0.3;
}

.recent-section {
  margin-bottom: var(--spacing-3xl);
}

/* Features */
.features-title {
  text-align: center;
  margin-bottom: var(--spacing-lg);
  font-size: 1.25rem;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--spacing-md);
}

.feature-card {
  padding: var(--spacing-lg);
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  transition: all var(--transition-normal);
}

.feature-card:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.feature-icon-wrapper {
  width: 44px;
  height: 44px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-md);
}

.icon-detect {
  background: var(--color-info-light);
  color: var(--color-info);
}

.icon-analyze {
  background: var(--color-success-light);
  color: var(--color-success);
}

.icon-ai {
  background: rgba(168, 85, 247, 0.12);
  color: var(--color-secondary);
}

.feature-card h3 {
  margin: 0 0 6px 0;
  font-size: 15px;
}

.feature-card p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 13px;
  line-height: 1.6;
}
</style>
