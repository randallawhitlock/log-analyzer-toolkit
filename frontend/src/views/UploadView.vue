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
  max-width: 800px;
  margin: 0 auto;
  padding: 40px 24px;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.back-link {
  display: inline-block;
  color: var(--color-text-muted, #888);
  text-decoration: none;
  margin-bottom: 24px;
}

.back-link:hover {
  color: var(--color-primary, #646cff);
}

.page-header h1 {
  margin: 0 0 12px 0;
  font-size: 2rem;
}

.page-subtitle {
  color: var(--color-text-muted, #888);
  margin: 0;
}

.formats-section {
  margin-top: 64px;
}

.formats-section h2 {
  text-align: center;
  margin-bottom: 24px;
}

.formats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.format-card {
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
  padding: 12px 16px;
}

.format-card h3 {
  margin: 0 0 6px 0;
  font-size: 14px;
  text-transform: uppercase;
  color: var(--color-primary, #646cff);
}

.format-card p {
  margin: 0;
  font-size: 12px;
  color: var(--color-text-muted, #888);
}

.loading-formats {
  text-align: center;
  color: var(--color-text-muted, #888);
}
</style>
