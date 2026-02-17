<template>
  <div class="analyses-list-view">
    <header class="page-header">
      <router-link to="/" class="back-link">← Back to Home</router-link>
      <h1>All Analyses</h1>
    </header>

    <!-- Filters -->
    <div class="filters">
      <div class="filter-group">
        <input
          v-model="searchQuery"
          @input="debouncedSearch"
          type="text"
          placeholder="🔍 Search filenames..."
          class="search-input"
        />
        <select v-model="formatFilter" @change="loadAnalyses" class="filter-select">
          <option value="">All Formats</option>
          <option v-for="format in availableFormats" :key="format" :value="format">
            {{ format }}
          </option>
        </select>
        <label class="error-filter">
          <input type="checkbox" v-model="showErrorsOnly" @change="loadAnalyses" />
          <span>Errors only</span>
        </label>
      </div>
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
const allAnalyses = ref([]) // Store all analyses for client-side filtering
const total = ref(0)
const currentPage = ref(1)
const perPage = 20
const formatFilter = ref('')
const searchQuery = ref('')
const showErrorsOnly = ref(false)
const availableFormats = ref([])

let searchTimeout = null
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    filterAnalyses()
  }, 300)
}

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
  if (!dateStr) return 'Unknown'
  // Append 'Z' to indicate UTC if not present
  const utcStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`
  const date = new Date(utcStr)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const loadAnalyses = async () => {
  try {
    const data = await getAnalyses({
      skip: 0,
      limit: 200 // Load more for client-side filtering
    })
    allAnalyses.value = data.analyses

    // Extract unique formats for filter
    if (availableFormats.value.length === 0) {
      const formats = new Set(data.analyses.map(a => a.detected_format))
      availableFormats.value = Array.from(formats).sort()
    }

    filterAnalyses()
  } catch (err) {
    console.error('Failed to load analyses:', err)
  }
}

const filterAnalyses = () => {
  let filtered = [...allAnalyses.value]

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(a => a.filename.toLowerCase().includes(query))
  }

  // Filter by format
  if (formatFilter.value) {
    filtered = filtered.filter(a => a.detected_format === formatFilter.value)
  }

  // Filter by errors only
  if (showErrorsOnly.value) {
    filtered = filtered.filter(a => a.error_rate > 0)
  }

  total.value = filtered.length

  // Apply pagination
  const start = (currentPage.value - 1) * perPage
  analyses.value = filtered.slice(start, start + perPage)
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
  max-width: 1100px;
  margin: 0 auto;
  padding: var(--spacing-lg);
}

.page-header {
  margin-bottom: var(--spacing-lg);
}

.back-link {
  color: var(--color-text-muted);
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
  font-size: 13px;
}

.back-link:hover {
  color: var(--color-primary);
}

.page-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.filters {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
  gap: 10px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.search-input {
  padding: 8px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: 13px;
  min-width: 200px;
  transition: all var(--transition-fast);
}

.search-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-light);
}

.search-input::placeholder {
  color: var(--color-text-dim);
}

.error-filter {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--color-text-muted);
  font-size: 13px;
  cursor: pointer;
}

.error-filter input[type="checkbox"] {
  width: 14px;
  height: 14px;
  accent-color: var(--color-primary);
}

.filter-select {
  padding: 8px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  font-size: 13px;
}

.upload-btn,
.upload-btn-large {
  padding: 8px 18px;
  background: var(--color-primary);
  color: white;
  text-decoration: none;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-size: 13px;
  transition: all var(--transition-fast);
}

.upload-btn:hover,
.upload-btn-large:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.upload-btn-large {
  padding: 12px 24px;
  font-size: 14px;
}

/* Loading & Empty States */
.loading-state,
.empty-state {
  text-align: center;
  padding: 80px var(--spacing-lg);
}

.spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--color-border);
  border-top-color: var(--color-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
  opacity: 0.6;
}

.empty-state h2 {
  margin: 0 0 6px 0;
  font-size: 1.25rem;
}

.empty-state p {
  color: var(--color-text-muted);
  margin: 0 0 20px 0;
  font-size: 14px;
}

/* Table */
.analyses-table-container {
  overflow-x: auto;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.analyses-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--color-bg-secondary);
}

.analyses-table th,
.analyses-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

.analyses-table th {
  background: var(--color-bg-tertiary);
  font-weight: 600;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--color-text-dim);
}

.analyses-table tr:last-child td {
  border-bottom: none;
}

.analyses-table tr:hover {
  background: var(--color-bg-hover);
}

.filename-cell {
  max-width: 300px;
}

.filename-link {
  color: var(--color-primary);
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
}

.filename-link:hover {
  text-decoration: underline;
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

.rate-success { color: var(--color-success); font-weight: 600; font-variant-numeric: tabular-nums; }
.rate-warning { color: var(--color-warning); font-weight: 600; font-variant-numeric: tabular-nums; }
.rate-error { color: var(--color-error); font-weight: 600; font-variant-numeric: tabular-nums; }

.date-cell {
  white-space: nowrap;
  font-size: 12px;
  color: var(--color-text-dim);
}

.actions-cell {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 5px 10px;
  font-size: 11px;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-decoration: none;
  font-weight: 600;
  transition: all var(--transition-fast);
}

.view-btn {
  background: var(--color-bg-tertiary);
  color: var(--color-text);
}

.view-btn:hover {
  background: var(--color-primary);
  color: white;
}

.delete-btn {
  background: transparent;
  color: var(--color-text-dim);
}

.delete-btn:hover {
  background: var(--color-error);
  color: white;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: var(--spacing-lg);
}

.page-btn {
  padding: 6px 14px;
  background: var(--color-bg-secondary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  color: var(--color-text);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--transition-fast);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-primary);
  background: var(--color-bg-hover);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: var(--color-text-muted);
}
</style>
