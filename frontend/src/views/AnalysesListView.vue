<template>
  <div class="analyses-list-view">
    <header class="page-header">
      <router-link to="/" class="back-link">← Back to Home</router-link>
      <h1>All Analyses</h1>
    </header>

    <!-- Filters -->
    <div class="filters">
      <select v-model="formatFilter" @change="loadAnalyses" class="filter-select">
        <option value="">All Formats</option>
        <option v-for="format in availableFormats" :key="format" :value="format">
          {{ format }}
        </option>
      </select>
      <router-link to="/upload" class="upload-btn">+ Upload New</router-link>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading analyses...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="analyses.length === 0" class="empty-state">
      <span class="empty-icon">📂</span>
      <h2>No analyses yet</h2>
      <p>Upload a log file to get started</p>
      <router-link to="/upload" class="upload-btn-large">Upload Log File</router-link>
    </div>

    <!-- Analyses Table -->
    <div v-else class="analyses-table-container">
      <table class="analyses-table">
        <thead>
          <tr>
            <th>Filename</th>
            <th>Format</th>
            <th>Lines</th>
            <th>Parse Rate</th>
            <th>Error Rate</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="analysis in analyses" :key="analysis.id">
            <td class="filename-cell">
              <router-link :to="`/analysis/${analysis.id}`" class="filename-link">
                {{ analysis.filename }}
              </router-link>
            </td>
            <td>
              <span class="format-badge">{{ analysis.detected_format }}</span>
            </td>
            <td>{{ analysis.total_lines.toLocaleString() }}</td>
            <td>
              <span :class="getSuccessClass(analysis.parse_success_rate)">
                {{ analysis.parse_success_rate.toFixed(1) }}%
              </span>
            </td>
            <td>
              <span :class="getErrorClass(analysis.error_rate)">
                {{ analysis.error_rate.toFixed(1) }}%
              </span>
            </td>
            <td class="date-cell">{{ formatDate(analysis.created_at) }}</td>
            <td class="actions-cell">
              <router-link :to="`/analysis/${analysis.id}`" class="action-btn view-btn">
                View
              </router-link>
              <button @click="confirmDelete(analysis)" class="action-btn delete-btn">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <button 
          @click="goToPage(currentPage - 1)" 
          :disabled="currentPage <= 1"
          class="page-btn"
        >
          ← Previous
        </button>
        <span class="page-info">
          Page {{ currentPage }} of {{ totalPages }} ({{ total }} total)
        </span>
        <button 
          @click="goToPage(currentPage + 1)" 
          :disabled="currentPage >= totalPages"
          class="page-btn"
        >
          Next →
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useApi } from '../composables/useApi'

const { getAnalyses, deleteAnalysis, loading, error } = useApi()

const analyses = ref([])
const total = ref(0)
const currentPage = ref(1)
const perPage = 20
const formatFilter = ref('')
const availableFormats = ref([])

const totalPages = computed(() => Math.ceil(total.value / perPage))

const getSuccessClass = (rate) => {
  if (rate >= 90) return 'rate-success'
  if (rate >= 70) return 'rate-warning'
  return 'rate-error'
}

const getErrorClass = (rate) => {
  if (rate <= 1) return 'rate-success'
  if (rate <= 5) return 'rate-warning'
  return 'rate-error'
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const loadAnalyses = async () => {
  try {
    const data = await getAnalyses({
      skip: (currentPage.value - 1) * perPage,
      limit: perPage,
      format: formatFilter.value || null
    })
    analyses.value = data.analyses
    total.value = data.total
    
    // Extract unique formats for filter
    if (availableFormats.value.length === 0) {
      const allData = await getAnalyses({ limit: 100 })
      const formats = new Set(allData.analyses.map(a => a.detected_format))
      availableFormats.value = Array.from(formats).sort()
    }
  } catch (err) {
    console.error('Failed to load analyses:', err)
  }
}

const goToPage = (page) => {
  currentPage.value = page
  loadAnalyses()
}

const confirmDelete = async (analysis) => {
  if (!confirm(`Delete analysis "${analysis.filename}"?`)) return
  
  try {
    await deleteAnalysis(analysis.id)
    await loadAnalyses()
  } catch (err) {
    console.error('Delete failed:', err)
    alert('Failed to delete analysis')
  }
}

onMounted(() => {
  loadAnalyses()
})
</script>

<style scoped>
.analyses-list-view {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 24px;
}

.back-link {
  color: var(--color-text-muted, #888);
  text-decoration: none;
  display: inline-block;
  margin-bottom: 12px;
}

.back-link:hover {
  color: var(--color-primary, #646cff);
}

.page-header h1 {
  margin: 0;
  font-size: 1.75rem;
}

.filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.filter-select {
  padding: 10px 16px;
  background: var(--color-bg-secondary, #1a1a2e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 8px;
  color: var(--color-text, #fff);
  font-size: 14px;
}

.upload-btn,
.upload-btn-large {
  padding: 10px 20px;
  background: var(--color-primary, #646cff);
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s ease;
}

.upload-btn:hover,
.upload-btn-large:hover {
  transform: translateY(-2px);
}

.upload-btn-large {
  padding: 14px 28px;
  font-size: 16px;
}

/* Loading & Empty States */
.loading-state,
.empty-state {
  text-align: center;
  padding: 80px 24px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border, #3a3a55);
  border-top-color: var(--color-primary, #646cff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 64px;
  display: block;
  margin-bottom: 16px;
}

.empty-state h2 {
  margin: 0 0 8px 0;
}

.empty-state p {
  color: var(--color-text-muted, #888);
  margin: 0 0 24px 0;
}

/* Table */
.analyses-table-container {
  overflow-x: auto;
}

.analyses-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-bg-secondary, #1a1a2e);
  border-radius: 12px;
  overflow: hidden;
}

.analyses-table th,
.analyses-table td {
  padding: 14px 16px;
  text-align: left;
  border-bottom: 1px solid var(--color-border, #3a3a55);
}

.analyses-table th {
  background: var(--color-bg-tertiary, #2a2a4e);
  font-weight: 600;
  font-size: 13px;
  text-transform: uppercase;
  color: var(--color-text-muted, #888);
}

.analyses-table tr:last-child td {
  border-bottom: none;
}

.analyses-table tr:hover {
  background: var(--color-bg-hover, rgba(100, 108, 255, 0.05));
}

.filename-cell {
  max-width: 300px;
}

.filename-link {
  color: var(--color-primary, #646cff);
  text-decoration: none;
  font-weight: 500;
}

.filename-link:hover {
  text-decoration: underline;
}

.format-badge {
  background: var(--color-bg-tertiary, #2a2a4e);
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 11px;
  text-transform: uppercase;
  font-weight: 600;
}

.rate-success { color: var(--color-success, #4caf50); font-weight: 600; }
.rate-warning { color: var(--color-warning, #ff9800); font-weight: 600; }
.rate-error { color: var(--color-error, #f44336); font-weight: 600; }

.date-cell {
  white-space: nowrap;
  font-size: 13px;
  color: var(--color-text-muted, #888);
}

.actions-cell {
  display: flex;
  gap: 8px;
}

.action-btn {
  padding: 6px 12px;
  font-size: 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.2s ease;
}

.view-btn {
  background: var(--color-bg-tertiary, #2a2a4e);
  color: var(--color-text, #fff);
}

.view-btn:hover {
  background: var(--color-primary, #646cff);
}

.delete-btn {
  background: transparent;
  color: var(--color-text-muted, #888);
}

.delete-btn:hover {
  background: var(--color-error, #f44336);
  color: white;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 24px;
}

.page-btn {
  padding: 8px 16px;
  background: var(--color-bg-tertiary, #2a2a4e);
  border: 1px solid var(--color-border, #3a3a55);
  border-radius: 6px;
  color: var(--color-text, #fff);
  cursor: pointer;
  transition: all 0.2s ease;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary, #646cff);
}

.page-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-info {
  font-size: 14px;
  color: var(--color-text-muted, #888);
}
</style>
