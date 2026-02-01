<template>
  <div class="home-view">
    <header class="hero">
      <h1 class="hero-title">
        <span class="logo-icon">📊</span>
        Log Analyzer <span class="accent">Pro</span>
      </h1>
      <p class="hero-subtitle">
        Intelligent log analysis and AI-powered troubleshooting
      </p>
    </header>

    <section class="upload-section">
      <LogUpload @upload-complete="handleUploadComplete" />
    </section>

    <section class="recent-section" v-if="recentAnalyses.length > 0">
      <div class="section-header">
        <h2>Recent Analyses</h2>
        <router-link to="/analyses" class="view-all">
          View All →
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
            <span class="dot">•</span>
            <span>{{ formatDate(analysis.created_at) }}</span>
          </div>
        </router-link>
      </div>
    </section>

    <section class="features-section">
      <h2>Features</h2>
      <div class="features-grid">
        <div class="feature-card">
          <span class="feature-icon">🔍</span>
          <h3>Auto-Detection</h3>
          <p>Automatically detects 15+ log formats including Apache, Nginx, Syslog, and more</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">📈</span>
          <h3>Deep Analysis</h3>
          <p>Extract error patterns, severity breakdowns, time analysis, and key metrics</p>
        </div>
        <div class="feature-card">
          <span class="feature-icon">🤖</span>
          <h3>AI-Powered Triage</h3>
          <p>Get intelligent recommendations using multiple AI providers</p>
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
  // Navigation is handled in LogUpload component
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
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 24px;
}

.hero {
  text-align: center;
  margin-bottom: 48px;
}

.hero-title {
  font-size: 3rem;
  font-weight: 800;
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.logo-icon {
  font-size: 3.5rem;
}

.accent {
  background: linear-gradient(135deg, var(--color-primary, #646cff), var(--color-secondary, #9c27b0));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1.2rem;
  color: var(--color-text-muted, #888);
  margin-top: 12px;
}

.upload-section {
  margin-bottom: 64px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.section-header h2 {
  margin: 0;
  font-size: 1.5rem;
}

.view-all {
  color: var(--color-primary, #646cff);
  text-decoration: none;
  font-weight: 500;
}

.view-all:hover {
  text-decoration: underline;
}

.recent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.recent-card {
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 12px;
  padding: 16px;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s ease;
}

.recent-card:hover {
  border-color: var(--color-primary, #646cff);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.format-badge {
  background: var(--color-bg-tertiary, #2a2a4e);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}

.success-rate {
  font-weight: 700;
  font-size: 14px;
}

.success-rate.success { color: var(--color-success, #4caf50); }
.success-rate.warning { color: var(--color-warning, #ff9800); }
.success-rate.error { color: var(--color-error, #f44336); }

.card-title {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-meta {
  font-size: 12px;
  color: var(--color-text-dim, #666);
  display: flex;
  align-items: center;
  gap: 6px;
}

.dot {
  opacity: 0.5;
}

.recent-section {
  margin-bottom: 64px;
}

.features-section h2 {
  text-align: center;
  margin-bottom: 24px;
}

.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.feature-card {
  text-align: center;
  padding: 32px 24px;
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 16px;
}

.feature-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.feature-card h3 {
  margin: 0 0 8px 0;
}

.feature-card p {
  margin: 0;
  color: var(--color-text-muted, #888);
  font-size: 14px;
}
</style>
