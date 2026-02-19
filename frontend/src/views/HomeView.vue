<template>
  <div class="home-view">
    <!-- Animated Background Glows -->
    <div class="bg-glow glow-1"></div>
    <div class="bg-glow glow-2"></div>

    <header class="hero animate-slide-up stagger-1">
      <div class="hero-badge">Intelligent Log Analysis</div>
      <h1 class="hero-title">
        Log Analyzer <span class="text-gradient">Pro</span>
      </h1>
      <p class="hero-subtitle">
        Upload, analyze, and troubleshoot log files with AI-powered insights.
      </p>
    </header>

    <section class="upload-section animate-slide-up stagger-2">
      <LogUpload @upload-complete="handleUploadComplete" />
    </section>

    <section class="recent-section animate-slide-up stagger-3" v-if="loadingRecent || recentAnalyses.length > 0">
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
        <!-- Skeleton Loaders -->
        <template v-if="loadingRecent">
          <div v-for="i in 3" :key="`skeleton-${i}`" class="recent-card skeleton">
            <div class="skeleton-header">
              <div class="skeleton-pill"></div>
              <div class="skeleton-rate"></div>
            </div>
            <div class="skeleton-line title"></div>
            <div class="skeleton-line meta"></div>
          </div>
        </template>

        <!-- Actual Cards -->
        <template v-else>
          <router-link
            v-for="analysis in recentAnalyses"
            :key="analysis.id"
            :to="`/analysis/${analysis.id}`"
            class="recent-card hover-lift"
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
        </template>
      </div>
    </section>

    <section class="features-section">
      <h2 class="features-title animate-slide-up stagger-4">What you can do</h2>
      <div class="features-grid">
        <div class="feature-card animate-slide-up stagger-3 interactive-tilt">
          <div class="feature-icon-wrapper icon-detect">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <h3>Auto-Detection</h3>
          <p>Automatically detects 15+ log formats including Apache, Nginx, Syslog, JSON, and more.</p>
        </div>
        <div class="feature-card animate-slide-up stagger-4 interactive-tilt">
          <div class="feature-icon-wrapper icon-analyze">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <path d="M3 3v18h18"/>
              <path d="m7 16 4-8 4 5 5-10"/>
            </svg>
          </div>
          <h3>Deep Analysis</h3>
          <p>Extract error patterns, severity breakdowns, time analysis, and key metrics at a glance.</p>
        </div>
        <div class="feature-card animate-slide-up stagger-5 interactive-tilt">
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
const loadingRecent = ref(true)

const handleUploadComplete = (analysis) => {
  console.log('Upload complete:', analysis.id)
}

const getSuccessClass = (rate) => {
  if (rate >= 90) return 'text-success'
  if (rate >= 70) return 'text-warning'
  return 'text-error'
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
    const data = await getAnalyses({ limit: 3 }) // 3 to fit grid perfectly
    recentAnalyses.value = data.analyses
  } catch (error) {
    console.error('Failed to load recent analyses:', error)
  } finally {
    loadingRecent.value = false
  }
})
</script>

<style scoped>
.home-view {
  max-width: 1080px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
  position: relative;
  overflow: hidden;
}

/* Background Glows */
.bg-glow {
  position: absolute;
  width: 600px;
  height: 600px;
  border-radius: 50%;
  filter: blur(140px);
  z-index: -1;
  opacity: 0.12;
  animation: pulseGlow 10s infinite alternate;
  pointer-events: none;
}

.glow-1 {
  top: -200px;
  left: -200px;
  background: var(--color-primary);
}

.glow-2 {
  bottom: 0px;
  right: -200px;
  background: var(--color-accent);
  animation-delay: -5s;
}

.hero {
  text-align: center;
  margin-bottom: var(--spacing-3xl);
  position: relative;
  z-index: 1;
}

.hero-badge {
  display: inline-block;
  padding: 6px 16px;
  border-radius: var(--radius-full);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--color-primary);
  background: var(--color-primary-light);
  border: 1px solid rgba(99, 102, 241, 0.3);
  margin-bottom: var(--spacing-lg);
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.2);
}

.hero-title {
  font-size: clamp(2.5rem, 6vw, 4rem);
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1.1;
  margin: 0;
  color: var(--color-text);
}

.hero-subtitle {
  font-size: 1.125rem;
  color: var(--color-text-muted);
  margin-top: 20px;
  max-width: 520px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

.upload-section {
  margin-bottom: var(--spacing-3xl);
  position: relative;
  z-index: 2;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-md);
  padding: 0 4px;
}

.section-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.view-all {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-muted);
  font-weight: 500;
  font-size: 0.875rem;
}

.view-all:hover {
  color: var(--color-primary);
  transform: translateX(2px);
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.recent-card {
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--spacing-xl);
  text-decoration: none;
  color: inherit;
  transition: all var(--transition-spring);
  position: relative;
  overflow: hidden;
}

.hover-lift:hover {
  border-color: var(--color-border-hover);
  box-shadow: var(--shadow-lg);
  transform: translateY(-4px);
}

.hover-lift::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  box-shadow: inset 0 0 0 1px var(--color-border-active);
  border-radius: inherit;
  opacity: 0;
  transition: opacity var(--transition-normal);
  pointer-events: none;
}

.hover-lift:hover::after {
  opacity: 1;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.format-badge {
  background: var(--color-bg-tertiary);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.6875rem;
  text-transform: uppercase;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-text-muted);
}

.success-rate {
  font-weight: 700;
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
}

.text-success { color: var(--color-success); }
.text-warning { color: var(--color-warning); }
.text-error { color: var(--color-error); }

.card-title {
  margin: 0 0 10px 0;
  font-size: 1.125rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 0.8125rem;
  color: var(--color-text-dim);
  display: flex;
  align-items: center;
  gap: 8px;
}

.separator {
  opacity: 0.3;
}

/* Skeleton Loaders */
.skeleton {
  pointer-events: none;
}
.skeleton-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 14px;
}
.skeleton-pill {
  width: 60px;
  height: 20px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite;
}
.skeleton-rate {
  width: 40px;
  height: 20px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite;
}
.skeleton-line {
  height: 16px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-sm);
  animation: pulse 1.5s infinite;
}
.skeleton-line.title {
  width: 80%;
  margin-bottom: 14px;
  height: 20px;
}
.skeleton-line.meta {
  width: 60%;
}

.recent-section {
  margin-bottom: var(--spacing-3xl);
  position: relative;
  z-index: 2;
}

/* Features */
.features-title {
  text-align: center;
  margin-bottom: var(--spacing-xl);
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.feature-card {
  padding: var(--spacing-xl);
  background: var(--glass-bg);
  backdrop-filter: var(--glass-blur);
  -webkit-backdrop-filter: var(--glass-blur);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  transition: all var(--transition-spring);
  position: relative;
  overflow: hidden;
}

.interactive-tilt:hover {
  border-color: var(--color-border-hover);
  transform: translateY(-6px) scale(1.02);
  box-shadow: var(--shadow-lg);
  background: var(--color-bg-elevated);
}

.feature-icon-wrapper {
  width: 52px;
  height: 52px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--spacing-lg);
  box-shadow: inset 0 2px 4px rgba(255,255,255,0.1);
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
  background: var(--color-secondary-glow);
  color: var(--color-secondary);
}

.feature-card h3 {
  margin: 0 0 10px 0;
  font-size: 1.125rem;
  color: var(--color-text);
}

.feature-card p {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 0.875rem;
  line-height: 1.6;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
