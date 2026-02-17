<template>
  <div class="upload-view">
    <header class="page-header">
      <router-link to="/" class="back-link">← Back to Home</router-link>
      <h1>Upload Log File</h1>
      <p class="page-subtitle">
        Upload a log file for analysis. We support 15+ log formats.
      </p>
    </header>

    <LogUpload />

    <section class="formats-section">
      <h2>Supported Formats</h2>
      <div v-if="formats.length > 0" class="formats-grid">
        <div v-for="format in formats" :key="format.name" class="format-card">
          <h3>{{ format.name }}</h3>
          <p>{{ truncateDescription(format.description) }}</p>
        </div>
      </div>
      <p v-else class="loading-formats">Loading supported formats...</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import LogUpload from '../components/LogUpload.vue'
import { useApi } from '../composables/useApi'

const { getFormats } = useApi()
const formats = ref([])

const truncateDescription = (desc) => {
  if (!desc) return ''
  // Extract first sentence from docstring
  const firstSentence = desc.split('.')[0]
  return firstSentence.length > 80 ? firstSentence.substring(0, 77) + '...' : firstSentence
}

onMounted(async () => {
  try {
    const data = await getFormats()
    formats.value = data.formats
  } catch (error) {
    console.error('Failed to load formats:', error)
  }
})
</script>

<style scoped>
.upload-view {
  max-width: 720px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

.page-header {
  text-align: center;
  margin-bottom: var(--spacing-2xl);
}

.back-link {
  display: inline-block;
  color: var(--color-text-muted);
  text-decoration: none;
  margin-bottom: var(--spacing-lg);
  font-size: 13px;
}

.back-link:hover {
  color: var(--color-primary);
}

.page-header h1 {
  margin: 0 0 8px 0;
  font-size: 1.75rem;
}

.page-subtitle {
  color: var(--color-text-muted);
  margin: 0;
  font-size: 14px;
}

.formats-section {
  margin-top: var(--spacing-3xl);
}

.formats-section h2 {
  text-align: center;
  margin-bottom: var(--spacing-lg);
  font-size: 1.25rem;
}

.formats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 10px;
}

.format-card {
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  transition: all var(--transition-fast);
}

.format-card:hover {
  border-color: var(--color-border-hover);
}

.format-card h3 {
  margin: 0 0 4px 0;
  font-size: 12px;
  text-transform: uppercase;
  color: var(--color-primary);
  letter-spacing: 0.04em;
  font-weight: 700;
}

.format-card p {
  margin: 0;
  font-size: 11px;
  color: var(--color-text-muted);
  line-height: 1.4;
}

.loading-formats {
  text-align: center;
  color: var(--color-text-muted);
  font-size: 13px;
}
</style>
